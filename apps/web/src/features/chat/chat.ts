import { z } from 'zod'

import { ApiError } from '@/lib/api'

const CHAT_MESSAGE_MAX_CODE_POINTS = 10_000
const CHAT_MESSAGE_PAGE_SIZE = 50

const awareDateTimeSchema = z.string().datetime({ offset: true })

const chatMessageSchema = z
  .object({
    id: z.string().uuid(),
    sender: z.enum(['self', 'buddy']),
    body: z.string().max(CHAT_MESSAGE_MAX_CODE_POINTS),
    created_at: awareDateTimeSchema,
    read_at: awareDateTimeSchema.nullable(),
  })
  .strict()

const chatMessagePageSchema = z
  .object({
    items: z.array(chatMessageSchema),
    next_before: z.string().min(1).max(64).nullable(),
    page_size: z.number().int().min(1).max(100),
  })
  .strict()
  .superRefine((page, context) => {
    const ids = page.items.map(({ id }) => id)
    if (new Set(ids).size !== ids.length) {
      context.addIssue({ code: 'custom', message: 'Duplicate chat message.' })
    }
    for (let index = 1; index < page.items.length; index += 1) {
      if (Date.parse(page.items[index - 1].created_at) > Date.parse(page.items[index].created_at)) {
        context.addIssue({ code: 'custom', message: 'Chat messages are not chronological.' })
        break
      }
    }
  })

const chatWebSocketEventSchema = z.discriminatedUnion('type', [
  z.object({ type: z.literal('chat.ready'), recovery: z.literal('history') }).strict(),
  z.object({ type: z.literal('chat.message.created'), message: chatMessageSchema }).strict(),
  z
    .object({
      type: z.literal('chat.message.accepted'),
      message_id: z.string().uuid(),
      realtime_delivery: z.enum(['published', 'already_published', 'unavailable']),
      recovery: z.literal('history'),
    })
    .strict(),
  z
    .object({
      type: z.literal('chat.error'),
      code: z.enum([
        'CHAT_EVENT_INVALID',
        'CHAT_MESSAGE_INVALID',
        'CHAT_IDEMPOTENCY_KEY_REUSED',
        'CHAT_RATE_LIMITED',
        'CHAT_REALTIME_UNAVAILABLE',
      ]),
      recoverable: z.boolean(),
    })
    .strict(),
])

type ChatMessage = Readonly<z.infer<typeof chatMessageSchema>>
type ChatMessagePage = Readonly<z.infer<typeof chatMessagePageSchema>>
type ChatWebSocketEvent = Readonly<z.infer<typeof chatWebSocketEventSchema>>

function parseContract<T>(schema: z.ZodType<T>, payload: unknown): T {
  const result = schema.safeParse(payload)
  if (!result.success) throw new ApiError(200, 'invalidResponse')
  return result.data
}

function parseChatMessage(payload: unknown): ChatMessage {
  return parseContract(chatMessageSchema, payload)
}

function parseChatMessagePage(payload: unknown): ChatMessagePage {
  return parseContract(chatMessagePageSchema, payload)
}

function parseChatWebSocketEvent(payload: unknown): ChatWebSocketEvent {
  return parseContract(chatWebSocketEventSchema, payload)
}

function countChatCodePoints(value: string): number {
  return Array.from(value).length
}

function isValidChatBody(value: string): boolean {
  return value.trim().length > 0 && countChatCodePoints(value) <= CHAT_MESSAGE_MAX_CODE_POINTS
}

function mergeChatMessages(
  pages: readonly ChatMessagePage[] | undefined,
  liveMessages: readonly ChatMessage[],
): ChatMessage[] {
  const seen = new Set<string>()
  const orderedPages = [...(pages ?? [])].reverse()
  return [...orderedPages.flatMap(({ items }) => items), ...liveMessages].filter(({ id }) => {
    if (seen.has(id)) return false
    seen.add(id)
    return true
  })
}

export {
  CHAT_MESSAGE_MAX_CODE_POINTS,
  CHAT_MESSAGE_PAGE_SIZE,
  chatMessagePageSchema,
  chatMessageSchema,
  chatWebSocketEventSchema,
  countChatCodePoints,
  isValidChatBody,
  mergeChatMessages,
  parseChatMessage,
  parseChatMessagePage,
  parseChatWebSocketEvent,
}
export type { ChatMessage, ChatMessagePage, ChatWebSocketEvent }
