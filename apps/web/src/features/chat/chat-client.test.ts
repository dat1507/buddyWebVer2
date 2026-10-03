import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { sessionClient } from '@/features/auth/session-client'
import { chatClient, chatUnreadWebSocketUrl, chatWebSocketUrl } from '@/features/chat/chat-client'

const conversationId = '20000000-0000-4000-8000-000000000001'
const clientMessageId = '20000000-0000-4000-8000-000000000002'
const messageId = '20000000-0000-4000-8000-000000000003'
const message = {
  id: messageId,
  sender: 'self',
  body: 'Hello',
  created_at: '2026-10-01T08:00:00Z',
  read_at: null,
}

describe('CHAT-004 API and WebSocket client', () => {
  beforeEach(() => {
    vi.stubEnv('VITE_API_URL', 'https://api.example.test/api')
  })

  afterEach(() => {
    vi.unstubAllEnvs()
    vi.restoreAllMocks()
  })

  it('uses only the opaque server cursor for bounded chronological history', async () => {
    const request = vi.spyOn(sessionClient, 'authenticatedJson').mockResolvedValue({
      items: [message],
      next_before: 'opaque-cursor',
      page_size: 50,
    })

    await expect(
      chatClient.readMessages({ conversationId, before: 'opaque-cursor' }),
    ).resolves.toMatchObject({ next_before: 'opaque-cursor' })
    expect(request).toHaveBeenCalledWith(
      `/chat/conversations/${conversationId}/messages?page_size=50&before=opaque-cursor`,
      { signal: undefined },
    )
  })

  it('sends the caller-owned stable client message ID and exact plain text', async () => {
    const request = vi.spyOn(sessionClient, 'authenticatedJson').mockResolvedValue(message)
    await expect(
      chatClient.sendMessage({ conversationId, clientMessageId, body: 'Hello' }),
    ).resolves.toEqual(message)
    expect(request).toHaveBeenCalledWith(`/chat/conversations/${conversationId}/messages`, {
      method: 'POST',
      body: { client_message_id: clientMessageId, body: 'Hello' },
    })
  })

  it('acknowledges only the supplied authoritative message boundary', async () => {
    const request = vi.spyOn(sessionClient, 'authenticatedJson').mockResolvedValue(undefined)
    await chatClient.acknowledgeMessages({ conversationId, throughMessageId: messageId })
    expect(request).toHaveBeenCalledWith(`/chat/conversations/${conversationId}/messages/read`, {
      method: 'POST',
      body: { through_message_id: messageId },
    })
  })

  it('reads the persisted unread summary without browser-owned state', async () => {
    const summary = {
      total_unread_messages: 1,
      conversations: [{ conversation_id: conversationId, unread_count: 1 }],
    }
    const request = vi.spyOn(sessionClient, 'authenticatedJson').mockResolvedValue(summary)
    await expect(chatClient.readUnreadSummary()).resolves.toEqual(summary)
    expect(request).toHaveBeenCalledWith('/chat/unread-summary', { signal: undefined })
  })

  it('derives a credential-free WSS URL with no query string', () => {
    const url = new URL(chatWebSocketUrl(conversationId))
    expect(url.href).toBe(`wss://api.example.test/api/ws/chat/${conversationId}`)
    expect(url.username).toBe('')
    expect(url.password).toBe('')
    expect(url.search).toBe('')
    expect(chatUnreadWebSocketUrl()).toBe('wss://api.example.test/api/ws/chat/notifications')
  })
})
