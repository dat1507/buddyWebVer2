import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useInfiniteQuery, useQueryClient } from '@tanstack/react-query'

import { chatClient, chatWebSocketUrl } from '@/features/chat/chat-client'
import { buddyUnreadQueryKeys } from '@/features/chat/buddy-unread-state'
import {
  CHAT_MESSAGE_PAGE_SIZE,
  isValidChatBody,
  mergeChatMessages,
  parseChatWebSocketEvent,
} from '@/features/chat/chat'
import type { ChatMessage } from '@/features/chat/chat'
import { ApiError } from '@/lib/api'

type ChatConnectionState = 'connecting' | 'connected' | 'reconnecting' | 'offline' | 'denied'

type PendingSendStatus = 'sending' | 'confirmed' | 'failed'

interface PendingChatMessage {
  clientMessageId: string
  body: string
  status: PendingSendStatus
  persistedMessageId: string | null
}

const chatQueryKeys = {
  conversation: (userId: string, conversationId: string) =>
    ['private', userId, 'chat', conversationId] as const,
}

const RECONNECT_DELAYS_MS = [1_000, 2_000, 5_000, 10_000, 10_000] as const
const SEND_ACK_TIMEOUT_MS = 5_000

function isAccessFailure(error: unknown): boolean {
  return error instanceof ApiError && [401, 403, 404].includes(error.status)
}

function useChatConversation({
  conversationId,
  userId,
}: {
  conversationId: string
  userId: string
}) {
  const queryClient = useQueryClient()
  const queryKey = chatQueryKeys.conversation(userId, conversationId)
  const [liveMessages, setLiveMessages] = useState<ChatMessage[]>([])
  const [pendingMessages, setPendingMessages] = useState<PendingChatMessage[]>([])
  const [connectionState, setConnectionState] = useState<ChatConnectionState>('connecting')
  const [accessDenied, setAccessDenied] = useState(false)
  const [connectionGeneration, setConnectionGeneration] = useState(0)
  const [visibilityGeneration, setVisibilityGeneration] = useState(0)

  const mountedRef = useRef(true)
  const liveMessagesRef = useRef<ChatMessage[]>([])
  const pendingMessagesRef = useRef<PendingChatMessage[]>([])
  const connectionStateRef = useRef<ChatConnectionState>('connecting')
  const accessDeniedRef = useRef(false)
  const socketRef = useRef<WebSocket | null>(null)
  const activeSocketSendRef = useRef<string | null>(null)
  const sendAckTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const httpFlightsRef = useRef(new Set<string>())
  const reconcileRef = useRef<() => Promise<void>>(async () => undefined)
  const sendHttpRef = useRef<(clientMessageId: string) => Promise<void>>(async () => undefined)
  const denyAccessRef = useRef<() => void>(() => undefined)

  const history = useInfiniteQuery({
    queryKey,
    queryFn: ({ pageParam, signal }) =>
      chatClient.readMessages({
        conversationId,
        before: pageParam,
        pageSize: CHAT_MESSAGE_PAGE_SIZE,
        signal,
      }),
    initialPageParam: null as string | null,
    getNextPageParam: (lastPage) => lastPage.next_before ?? undefined,
    retry: (failureCount, error) => !isAccessFailure(error) && failureCount < 1,
  })

  const commitLiveMessages = useCallback((update: (current: ChatMessage[]) => ChatMessage[]) => {
    const next = update(liveMessagesRef.current)
    liveMessagesRef.current = next
    if (mountedRef.current) setLiveMessages(next)
  }, [])

  const commitPendingMessages = useCallback(
    (update: (current: PendingChatMessage[]) => PendingChatMessage[]) => {
      const next = update(pendingMessagesRef.current)
      pendingMessagesRef.current = next
      if (mountedRef.current) setPendingMessages(next)
    },
    [],
  )

  const updateConnectionState = useCallback((next: ChatConnectionState) => {
    connectionStateRef.current = next
    if (mountedRef.current) setConnectionState(next)
  }, [])

  const appendLiveMessage = useCallback(
    (message: ChatMessage) => {
      commitLiveMessages((current) =>
        current.some(({ id }) => id === message.id) ? current : [...current, message],
      )
    },
    [commitLiveMessages],
  )

  const clearSendAckTimer = useCallback(() => {
    if (sendAckTimerRef.current !== null) clearTimeout(sendAckTimerRef.current)
    sendAckTimerRef.current = null
  }, [])

  const denyAccess = useCallback(() => {
    accessDeniedRef.current = true
    clearSendAckTimer()
    activeSocketSendRef.current = null
    socketRef.current?.close()
    queryClient.removeQueries({ queryKey, exact: true })
    liveMessagesRef.current = []
    pendingMessagesRef.current = []
    if (mountedRef.current) {
      setLiveMessages([])
      setPendingMessages([])
      setAccessDenied(true)
    }
    updateConnectionState('denied')
  }, [clearSendAckTimer, queryClient, queryKey, updateConnectionState])
  denyAccessRef.current = denyAccess

  const reconcileHistory = useCallback(async () => {
    await history.refetch()
  }, [history])
  reconcileRef.current = reconcileHistory

  const sendThroughHttp = useCallback(
    async (clientMessageId: string) => {
      if (httpFlightsRef.current.has(clientMessageId)) return
      const pending = pendingMessagesRef.current.find(
        (message) => message.clientMessageId === clientMessageId,
      )
      if (!pending) return
      httpFlightsRef.current.add(clientMessageId)
      commitPendingMessages((current) =>
        current.map((message) =>
          message.clientMessageId === clientMessageId ? { ...message, status: 'sending' } : message,
        ),
      )
      try {
        const persisted = await chatClient.sendMessage({
          conversationId,
          clientMessageId,
          body: pending.body,
        })
        if (!mountedRef.current) return
        appendLiveMessage(persisted)
        commitPendingMessages((current) =>
          current.filter((message) => message.clientMessageId !== clientMessageId),
        )
        void reconcileRef.current()
      } catch (error) {
        if (!mountedRef.current) return
        if (isAccessFailure(error)) {
          denyAccessRef.current()
          return
        }
        commitPendingMessages((current) =>
          current.map((message) =>
            message.clientMessageId === clientMessageId
              ? { ...message, status: 'failed' }
              : message,
          ),
        )
      } finally {
        httpFlightsRef.current.delete(clientMessageId)
      }
    },
    [appendLiveMessage, commitPendingMessages, conversationId],
  )
  sendHttpRef.current = sendThroughHttp

  useEffect(() => {
    if (isAccessFailure(history.error)) denyAccess()
  }, [denyAccess, history.error])

  useEffect(() => {
    let disposed = false
    let reconnectTimer: ReturnType<typeof setTimeout> | null = null
    let reconnectAttempt = 0

    const connect = () => {
      if (disposed || accessDeniedRef.current) return
      updateConnectionState(reconnectAttempt === 0 ? 'connecting' : 'reconnecting')
      let socket: WebSocket
      try {
        socket = new WebSocket(chatWebSocketUrl(conversationId))
      } catch {
        updateConnectionState('offline')
        return
      }
      socketRef.current = socket

      socket.addEventListener('message', (event) => {
        if (disposed || typeof event.data !== 'string') return
        let payload: unknown
        try {
          payload = JSON.parse(event.data) as unknown
        } catch {
          void reconcileRef.current()
          return
        }
        let serverEvent
        try {
          serverEvent = parseChatWebSocketEvent(payload)
        } catch {
          void reconcileRef.current()
          return
        }

        if (serverEvent.type === 'chat.ready') {
          reconnectAttempt = 0
          updateConnectionState('connected')
          void reconcileRef.current()
          return
        }
        if (serverEvent.type === 'chat.message.created') {
          appendLiveMessage(serverEvent.message)
          return
        }
        if (serverEvent.type === 'chat.message.accepted') {
          const clientMessageId = activeSocketSendRef.current
          if (!clientMessageId) return
          clearSendAckTimer()
          activeSocketSendRef.current = null
          commitPendingMessages((current) =>
            current.map((message) =>
              message.clientMessageId === clientMessageId
                ? {
                    ...message,
                    persistedMessageId: serverEvent.message_id,
                    status: 'confirmed',
                  }
                : message,
            ),
          )
          void reconcileRef.current()
          return
        }

        const clientMessageId = activeSocketSendRef.current
        if (
          clientMessageId &&
          ['CHAT_MESSAGE_INVALID', 'CHAT_IDEMPOTENCY_KEY_REUSED', 'CHAT_RATE_LIMITED'].includes(
            serverEvent.code,
          )
        ) {
          clearSendAckTimer()
          activeSocketSendRef.current = null
          commitPendingMessages((current) =>
            current.map((message) =>
              message.clientMessageId === clientMessageId
                ? { ...message, status: 'failed' }
                : message,
            ),
          )
        }
      })

      socket.addEventListener('close', (event) => {
        if (disposed || socketRef.current !== socket) return
        socketRef.current = null
        if (accessDeniedRef.current) return
        const clientMessageId = activeSocketSendRef.current
        if (clientMessageId) {
          clearSendAckTimer()
          activeSocketSendRef.current = null
          void sendHttpRef.current(clientMessageId)
        }
        if (
          event.code === 1008 &&
          event.reason !== 'CHAT_RATE_LIMITED' &&
          event.reason !== 'CHAT_EVENT_INVALID'
        ) {
          denyAccessRef.current()
          return
        }
        const delay = RECONNECT_DELAYS_MS[reconnectAttempt]
        if (delay === undefined) {
          updateConnectionState('offline')
          return
        }
        reconnectAttempt += 1
        updateConnectionState('reconnecting')
        reconnectTimer = setTimeout(connect, delay)
      })
    }

    connect()
    return () => {
      disposed = true
      if (reconnectTimer !== null) clearTimeout(reconnectTimer)
      clearSendAckTimer()
      activeSocketSendRef.current = null
      const socket = socketRef.current
      socketRef.current = null
      socket?.close(1000, 'CHAT_VIEW_CLOSED')
    }
  }, [
    appendLiveMessage,
    clearSendAckTimer,
    commitPendingMessages,
    connectionGeneration,
    conversationId,
    updateConnectionState,
  ])

  useEffect(() => {
    const onVisibilityChange = () => {
      if (document.visibilityState === 'visible') setVisibilityGeneration((value) => value + 1)
    }
    document.addEventListener('visibilitychange', onVisibilityChange)
    return () => document.removeEventListener('visibilitychange', onVisibilityChange)
  }, [])

  useEffect(() => {
    mountedRef.current = true
    return () => {
      mountedRef.current = false
    }
  }, [])

  const messages = useMemo(
    () => mergeChatMessages(history.data?.pages, liveMessages),
    [history.data?.pages, liveMessages],
  )
  const persistedIds = useMemo(() => new Set(messages.map(({ id }) => id)), [messages])

  useEffect(() => {
    if (!pendingMessages.some(({ persistedMessageId }) => persistedMessageId)) return
    commitPendingMessages((current) =>
      current.some(
        ({ persistedMessageId }) => persistedMessageId && persistedIds.has(persistedMessageId),
      )
        ? current.filter(
            ({ persistedMessageId }) =>
              !persistedMessageId || !persistedIds.has(persistedMessageId),
          )
        : current,
    )
  }, [commitPendingMessages, pendingMessages, persistedIds])

  const lastReadMessageRef = useRef<string | null>(null)
  const readFlightRef = useRef<string | null>(null)
  const latestIncomingMessageId = [...messages]
    .reverse()
    .find(({ sender }) => sender === 'buddy')?.id

  useEffect(() => {
    if (
      !latestIncomingMessageId ||
      document.visibilityState !== 'visible' ||
      lastReadMessageRef.current === latestIncomingMessageId ||
      readFlightRef.current === latestIncomingMessageId ||
      accessDenied
    ) {
      return
    }
    readFlightRef.current = latestIncomingMessageId
    void chatClient
      .acknowledgeMessages({ conversationId, throughMessageId: latestIncomingMessageId })
      .then(() => {
        lastReadMessageRef.current = latestIncomingMessageId
        void queryClient.invalidateQueries({
          queryKey: buddyUnreadQueryKeys.summary(userId),
          exact: true,
        })
      })
      .catch((error: unknown) => {
        if (isAccessFailure(error)) denyAccessRef.current()
      })
      .finally(() => {
        if (readFlightRef.current === latestIncomingMessageId) readFlightRef.current = null
      })
  }, [
    accessDenied,
    connectionState,
    conversationId,
    latestIncomingMessageId,
    queryClient,
    userId,
    visibilityGeneration,
  ])

  const dispatchPending = useCallback(
    (clientMessageId: string) => {
      const pending = pendingMessagesRef.current.find(
        (message) => message.clientMessageId === clientMessageId,
      )
      if (!pending) return
      const socket = socketRef.current
      if (
        connectionStateRef.current !== 'connected' ||
        !socket ||
        socket.readyState !== WebSocket.OPEN ||
        activeSocketSendRef.current
      ) {
        void sendHttpRef.current(clientMessageId)
        return
      }
      commitPendingMessages((current) =>
        current.map((message) =>
          message.clientMessageId === clientMessageId ? { ...message, status: 'sending' } : message,
        ),
      )
      activeSocketSendRef.current = clientMessageId
      try {
        socket.send(
          JSON.stringify({
            type: 'message.send',
            client_message_id: clientMessageId,
            body: pending.body,
          }),
        )
        sendAckTimerRef.current = setTimeout(() => {
          if (activeSocketSendRef.current !== clientMessageId) return
          activeSocketSendRef.current = null
          sendAckTimerRef.current = null
          void sendHttpRef.current(clientMessageId)
        }, SEND_ACK_TIMEOUT_MS)
      } catch {
        activeSocketSendRef.current = null
        void sendHttpRef.current(clientMessageId)
      }
    },
    [commitPendingMessages],
  )

  const sendMessage = useCallback(
    (body: string): boolean => {
      if (
        accessDenied ||
        !isValidChatBody(body) ||
        pendingMessagesRef.current.some(({ status }) => status === 'sending')
      ) {
        return false
      }
      const clientMessageId = crypto.randomUUID()
      commitPendingMessages((current) => [
        ...current,
        { clientMessageId, body, status: 'sending', persistedMessageId: null },
      ])
      dispatchPending(clientMessageId)
      return true
    },
    [accessDenied, commitPendingMessages, dispatchPending],
  )

  const retryMessage = useCallback(
    (clientMessageId: string) => {
      if (pendingMessagesRef.current.some(({ status }) => status === 'sending')) return
      dispatchPending(clientMessageId)
    },
    [dispatchPending],
  )

  return {
    accessDenied,
    connectionState,
    hasOlder: history.hasNextPage,
    historyError: history.error,
    isHistoryError: history.isError,
    isLoadingHistory: history.isPending,
    isLoadingOlder: history.isFetchingNextPage,
    isRefreshingHistory: history.isFetching && !history.isPending && !history.isFetchingNextPage,
    isSending: pendingMessages.some(({ status }) => status === 'sending'),
    loadOlder: history.fetchNextPage,
    messages,
    pendingMessages,
    refetchHistory: history.refetch,
    retryConnection: () => {
      accessDeniedRef.current = false
      setAccessDenied(false)
      setConnectionGeneration((value) => value + 1)
    },
    retryMessage,
    sendMessage,
  }
}

export { chatQueryKeys, useChatConversation }
export type { ChatConnectionState, PendingChatMessage }
