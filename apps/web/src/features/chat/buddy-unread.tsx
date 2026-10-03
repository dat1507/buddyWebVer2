import { useEffect, useMemo, type ReactNode } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'

import { parseChatUnreadWebSocketEvent } from '@/features/chat/chat'
import { chatClient, chatUnreadWebSocketUrl } from '@/features/chat/chat-client'
import {
  BuddyUnreadContext,
  EMPTY_UNREAD_SUMMARY,
  buddyUnreadQueryKeys,
} from '@/features/chat/buddy-unread-state'
import { useAuthStore } from '@/stores/auth-store'

const RECONNECT_DELAYS_MS = [1_000, 2_000, 5_000, 10_000, 30_000] as const
const UNREAD_RECONCILE_INTERVAL_MS = 15_000

export function BuddyUnreadProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient()
  const status = useAuthStore((state) => state.status)
  const user = useAuthStore((state) => state.user)
  const enabled =
    status === 'authenticated' && user?.role === 'USER' && user.email_verified === true
  const userId = enabled && user ? user.id : null
  const queryKey = useMemo(() => (userId ? buddyUnreadQueryKeys.summary(userId) : null), [userId])
  const unread = useQuery({
    queryKey: queryKey ?? ['private', 'anonymous', 'chat', 'unread-summary'],
    queryFn: ({ signal }) => chatClient.readUnreadSummary(signal),
    enabled: userId !== null,
    refetchInterval: userId ? UNREAD_RECONCILE_INTERVAL_MS : false,
    staleTime: 0,
  })

  useEffect(() => {
    if (!userId || !queryKey) return
    let disposed = false
    let reconnectAttempt = 0
    let reconnectTimer: ReturnType<typeof setTimeout> | null = null
    let socket: WebSocket | null = null

    const reconcile = () => {
      void queryClient.invalidateQueries({ queryKey, exact: true })
    }
    const connect = () => {
      if (disposed) return
      try {
        socket = new WebSocket(chatUnreadWebSocketUrl())
      } catch {
        reconnectTimer = setTimeout(connect, RECONNECT_DELAYS_MS.at(-1))
        return
      }
      const current = socket
      current.addEventListener('message', (event) => {
        if (disposed || typeof event.data !== 'string') return
        try {
          const payload = parseChatUnreadWebSocketEvent(JSON.parse(event.data) as unknown)
          if (payload.type === 'chat.unread.ready') reconnectAttempt = 0
          reconcile()
        } catch {
          reconcile()
        }
      })
      current.addEventListener('close', (event) => {
        if (disposed || socket !== current) return
        socket = null
        reconcile()
        if (event.code === 1008) return
        const delay =
          RECONNECT_DELAYS_MS[Math.min(reconnectAttempt, RECONNECT_DELAYS_MS.length - 1)]
        reconnectAttempt += 1
        reconnectTimer = setTimeout(connect, delay)
      })
    }

    connect()
    return () => {
      disposed = true
      if (reconnectTimer !== null) clearTimeout(reconnectTimer)
      socket?.close(1000, 'CHAT_UNREAD_VIEW_CLOSED')
    }
  }, [queryClient, queryKey, userId])

  const value = useMemo(
    () => ({ summary: unread.data ?? EMPTY_UNREAD_SUMMARY, isFetching: unread.isFetching }),
    [unread.data, unread.isFetching],
  )
  return <BuddyUnreadContext.Provider value={value}>{children}</BuddyUnreadContext.Provider>
}
