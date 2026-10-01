import { sessionClient } from '@/features/auth/session-client'
import {
  CHAT_MESSAGE_PAGE_SIZE,
  parseChatMessage,
  parseChatMessagePage,
} from '@/features/chat/chat'
import type { ChatMessage, ChatMessagePage } from '@/features/chat/chat'
import { ApiError } from '@/lib/api'

interface ReadChatMessagesRequest {
  conversationId: string
  before?: string | null
  pageSize?: number
  signal?: AbortSignal
}

interface SendChatMessageRequest {
  conversationId: string
  clientMessageId: string
  body: string
}

interface AcknowledgeChatMessagesRequest {
  conversationId: string
  throughMessageId: string
}

function conversationMessagesPath(conversationId: string): string {
  return `/chat/conversations/${encodeURIComponent(conversationId)}/messages`
}

function chatWebSocketUrl(conversationId: string): string {
  const configured = import.meta.env.VITE_API_URL?.replace(/\/+$/, '')
  if (!configured) throw new ApiError(0, 'configuration')
  let apiUrl: URL
  try {
    apiUrl = new URL(configured, window.location.origin)
  } catch {
    throw new ApiError(0, 'configuration')
  }
  if (apiUrl.protocol !== 'http:' && apiUrl.protocol !== 'https:') {
    throw new ApiError(0, 'configuration')
  }
  apiUrl.protocol = apiUrl.protocol === 'https:' ? 'wss:' : 'ws:'
  apiUrl.pathname = `${apiUrl.pathname.replace(/\/+$/, '')}/ws/chat/${encodeURIComponent(conversationId)}`
  apiUrl.search = ''
  apiUrl.hash = ''
  return apiUrl.toString()
}

const chatClient = {
  async readMessages({
    conversationId,
    before,
    pageSize = CHAT_MESSAGE_PAGE_SIZE,
    signal,
  }: ReadChatMessagesRequest): Promise<ChatMessagePage> {
    const search = new URLSearchParams({ page_size: String(pageSize) })
    if (before) search.set('before', before)
    return parseChatMessagePage(
      await sessionClient.authenticatedJson(
        `${conversationMessagesPath(conversationId)}?${search}`,
        { signal },
      ),
    )
  },
  async sendMessage({
    conversationId,
    clientMessageId,
    body,
  }: SendChatMessageRequest): Promise<ChatMessage> {
    return parseChatMessage(
      await sessionClient.authenticatedJson(conversationMessagesPath(conversationId), {
        method: 'POST',
        body: { client_message_id: clientMessageId, body },
      }),
    )
  },
  async acknowledgeMessages({
    conversationId,
    throughMessageId,
  }: AcknowledgeChatMessagesRequest): Promise<void> {
    await sessionClient.authenticatedJson(`${conversationMessagesPath(conversationId)}/read`, {
      method: 'POST',
      body: { through_message_id: throughMessageId },
    })
  },
}

export { chatClient, chatWebSocketUrl, conversationMessagesPath }
export type { AcknowledgeChatMessagesRequest, ReadChatMessagesRequest, SendChatMessageRequest }
