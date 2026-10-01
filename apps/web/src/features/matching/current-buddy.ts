import { z } from 'zod'

import { canonicalEmailReturnTo } from '@/features/auth/email-deep-link'
import { invitationProfileSchema, parseContract } from '@/features/matching/invitation'
import { compatibilityExplanationSchema } from '@/features/matching/recommendation'

const CURRENT_BUDDIES_PAGE_SIZE = 20

const isoDateSchema = z
  .string()
  .regex(/^\d{4}-\d{2}-\d{2}$/)
  .refine((value) => {
    const parsed = new Date(`${value}T00:00:00.000Z`)
    return !Number.isNaN(parsed.getTime()) && parsed.toISOString().startsWith(value)
  })

const currentBuddySchema = z
  .object({
    match_id: z.string().uuid(),
    conversation_id: z.string().uuid(),
    buddy: invitationProfileSchema,
    score: z.number().int().min(0).max(100),
    explanation: compatibilityExplanationSchema,
    reference_week_start: isoDateSchema,
  })
  .strict()

const currentBuddyListSchema = z
  .object({
    items: z.array(currentBuddySchema),
    page: z.number().int().min(1),
    page_size: z.number().int().min(1).max(50),
    total: z.number().int().min(0),
    total_pages: z.number().int().min(0),
  })
  .strict()
  .superRefine((value, context) => {
    const expectedPages = value.total === 0 ? 0 : Math.ceil(value.total / value.page_size)
    if (
      value.items.length > value.page_size ||
      value.total_pages !== expectedPages ||
      (value.total_pages > 0 && value.page > value.total_pages)
    ) {
      context.addIssue({ code: 'custom', message: 'Inconsistent Current Buddies pagination.' })
    }

    for (const [field, label] of [
      ['match_id', 'Match'],
      ['conversation_id', 'Conversation'],
    ] as const) {
      const identifiers = value.items.map((item) => item[field])
      if (new Set(identifiers).size !== identifiers.length) {
        context.addIssue({ code: 'custom', message: `Duplicate ${label}.` })
      }
    }
  })

type CurrentBuddy = Readonly<z.infer<typeof currentBuddySchema>>
type CurrentBuddyList = Readonly<z.infer<typeof currentBuddyListSchema>>

function parseCurrentBuddyList(payload: unknown): CurrentBuddyList {
  return parseContract(currentBuddyListSchema, payload)
}

function currentBuddyPath(conversationId: string): string {
  return `/user/buddy?conversation=${encodeURIComponent(conversationId)}`
}

function conversationIdFromBuddyLocation(location: {
  pathname: string
  search: string
  hash: string
}): string | null {
  const canonical = canonicalEmailReturnTo(`${location.pathname}${location.search}${location.hash}`)
  if (!canonical?.startsWith('/user/buddy?conversation=')) return null
  return new URLSearchParams(canonical.slice(canonical.indexOf('?'))).get('conversation')
}

function currentBuddiesDestination(conversationId: string | null): string {
  return conversationId
    ? `/user/matching?conversation=${conversationId}#current-buddies`
    : '/user/matching#current-buddies'
}

export {
  CURRENT_BUDDIES_PAGE_SIZE,
  conversationIdFromBuddyLocation,
  currentBuddiesDestination,
  currentBuddyListSchema,
  currentBuddyPath,
  parseCurrentBuddyList,
}
export type { CurrentBuddy, CurrentBuddyList }
