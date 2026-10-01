import { describe, expect, it } from 'vitest'

import {
  CHAT_MESSAGE_MAX_CODE_POINTS,
  countChatCodePoints,
  isValidChatBody,
  mergeChatMessages,
  parseChatMessagePage,
  parseChatWebSocketEvent,
} from '@/features/chat/chat'
import { ApiError } from '@/lib/api'

const older = {
  id: '10000000-0000-4000-8000-000000000001',
  sender: 'buddy' as const,
  body: 'Older',
  created_at: '2026-10-01T08:00:00Z',
  read_at: null,
}
const newer = {
  id: '10000000-0000-4000-8000-000000000002',
  sender: 'self' as const,
  body: 'Newer',
  created_at: '2026-10-01T08:01:00Z',
  read_at: null,
}

describe('CHAT-004 frontend contracts', () => {
  it('parses strict chronological history without exposing extra fields', () => {
    expect(
      parseChatMessagePage({ items: [older, newer], next_before: 'opaque', page_size: 50 }),
    ).toEqual({ items: [older, newer], next_before: 'opaque', page_size: 50 })

    expect(() =>
      parseChatMessagePage({
        items: [{ ...older, sender_id: 'private' }],
        next_before: null,
        page_size: 50,
      }),
    ).toThrow(ApiError)
    expect(() =>
      parseChatMessagePage({ items: [newer, older], next_before: null, page_size: 50 }),
    ).toThrow(ApiError)
    expect(() =>
      parseChatMessagePage({ items: [older, older], next_before: null, page_size: 50 }),
    ).toThrow(ApiError)
  })

  it('prepends opaque-cursor pages in server order and deduplicates realtime/history echoes', () => {
    const newestPage = { items: [newer], next_before: 'opaque', page_size: 50 }
    const olderPage = { items: [older], next_before: null, page_size: 50 }
    expect(mergeChatMessages([newestPage, olderPage], [newer])).toEqual([older, newer])
  })

  it('validates Unicode code points instead of UTF-16 code units', () => {
    const boundary = '🙂'.repeat(CHAT_MESSAGE_MAX_CODE_POINTS)
    expect(boundary.length).toBe(CHAT_MESSAGE_MAX_CODE_POINTS * 2)
    expect(countChatCodePoints(boundary)).toBe(CHAT_MESSAGE_MAX_CODE_POINTS)
    expect(isValidChatBody(boundary)).toBe(true)
    expect(isValidChatBody(`${boundary}a`)).toBe(false)
    expect(isValidChatBody(' \n\t ')).toBe(false)
  })

  it('accepts only the documented strict WebSocket event shapes', () => {
    expect(
      parseChatWebSocketEvent({
        type: 'chat.message.created',
        message: newer,
      }),
    ).toEqual({ type: 'chat.message.created', message: newer })
    expect(() =>
      parseChatWebSocketEvent({
        type: 'chat.message.created',
        message: newer,
        user_id: 'private',
      }),
    ).toThrow(ApiError)
    expect(() => parseChatWebSocketEvent({ type: 'typing.started' })).toThrow(ApiError)
  })
})
