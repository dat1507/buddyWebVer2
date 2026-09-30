import { z } from 'zod'

import {
  compatibilityExplanationSchema,
  languageSchema,
  preferenceSchema,
  weeklyAvailabilitySchema,
} from '@/features/matching/recommendation'
import { ApiError } from '@/lib/api'
import type { InvitationApiErrorReason } from '@/lib/api'

const INVITATION_PAGE_SIZE = 20
const MAX_INVITATION_MESSAGE_WORDS = 500
const MAX_INVITATION_MESSAGE_CODE_POINTS = 10_000

const isoDateSchema = z
  .string()
  .regex(/^\d{4}-\d{2}-\d{2}$/)
  .refine((value) => {
    const parsed = new Date(`${value}T00:00:00.000Z`)
    return !Number.isNaN(parsed.getTime()) && parsed.toISOString().startsWith(value)
  })

const awareDateTimeSchema = z.string().refine((value) => {
  if (!/(?:Z|[+-]\d{2}:\d{2})$/.test(value)) return false
  return !Number.isNaN(new Date(value).getTime())
})

const invitationAvatarSchema = z
  .object({
    id: z.string().uuid(),
    width: z.number().int().positive(),
    height: z.number().int().positive(),
  })
  .strict()

const invitationProfileSchema = z
  .object({
    id: z.string().uuid(),
    display_name: z.string().max(80).nullable(),
    student_type: z.enum(['VIETNAMESE', 'INTERNATIONAL']).nullable(),
    major: z.string().nullable(),
    avatar: invitationAvatarSchema.nullable(),
    interests: z.array(preferenceSchema).max(20),
    languages: z.array(languageSchema).max(10),
    activities: z.array(preferenceSchema).max(20),
    availability: weeklyAvailabilitySchema.nullable(),
  })
  .strict()

const invitationReadBase = {
  id: z.string().uuid(),
  created_at: awareDateTimeSchema,
  expires_at: awareDateTimeSchema,
  score: z.number().int().min(0).max(100).nullable(),
  explanation: compatibilityExplanationSchema.nullable(),
}

const incomingInvitationSchema = z
  .object({
    ...invitationReadBase,
    status: z.literal('PENDING'),
    sender: invitationProfileSchema,
    message: z.string().refine((value) => Array.from(value).length <= 10_000),
  })
  .strict()
  .refine(({ score, explanation }) => (score === null) === (explanation === null))

const sentInvitationSchema = z
  .object({
    ...invitationReadBase,
    status: z.enum(['PENDING', 'ACCEPTED']),
    recipient: invitationProfileSchema,
  })
  .strict()
  .refine(({ score, explanation }) => (score === null) === (explanation === null))

const invitationPagination = {
  page: z.number().int().min(1),
  page_size: z.number().int().min(1).max(50),
  total: z.number().int().min(0),
  total_pages: z.number().int().min(0),
  reference_week_start: isoDateSchema,
}

function validPagination({
  items,
  page_size,
  total,
  total_pages,
}: {
  items: readonly { id: string }[]
  page_size: number
  total: number
  total_pages: number
}): boolean {
  const expectedPages = total === 0 ? 0 : Math.ceil(total / page_size)
  return (
    items.length <= page_size &&
    total_pages === expectedPages &&
    new Set(items.map(({ id }) => id)).size === items.length
  )
}

const incomingInvitationListSchema = z
  .object({ items: z.array(incomingInvitationSchema), ...invitationPagination })
  .strict()
  .refine(validPagination)

const sentInvitationListSchema = z
  .object({ items: z.array(sentInvitationSchema), ...invitationPagination })
  .strict()
  .refine(validPagination)

const invitationCreateResponseSchema = z
  .object({
    id: z.string().uuid(),
    status: z.literal('PENDING'),
    expires_at: awareDateTimeSchema,
  })
  .strict()

const invitationAcceptResponseSchema = z
  .object({
    invitation_id: z.string().uuid(),
    status: z.literal('ACCEPTED'),
    match_id: z.string().uuid(),
    conversation_id: z.string().uuid(),
  })
  .strict()

const invitationMutationResponseSchema = z
  .object({
    invitation_id: z.string().uuid(),
    status: z.enum(['ACCEPTED', 'DECLINED', 'CANCELLED']),
  })
  .strict()

type InvitationProfile = Readonly<z.infer<typeof invitationProfileSchema>>
type IncomingInvitation = Readonly<z.infer<typeof incomingInvitationSchema>>
type SentInvitation = Readonly<z.infer<typeof sentInvitationSchema>>
type IncomingInvitationList = Readonly<z.infer<typeof incomingInvitationListSchema>>
type SentInvitationList = Readonly<z.infer<typeof sentInvitationListSchema>>
type InvitationCreateResponse = Readonly<z.infer<typeof invitationCreateResponseSchema>>
type InvitationAcceptResponse = Readonly<z.infer<typeof invitationAcceptResponseSchema>>
type InvitationMutationResponse = Readonly<z.infer<typeof invitationMutationResponseSchema>>
type InvitationAction = 'send' | 'accept' | 'decline' | 'cancel' | 'hide'
type InvitationMessageReason =
  'INVITATION_MESSAGE_TOO_MANY_WORDS' | 'INVITATION_MESSAGE_TOO_MANY_CODE_POINTS'

interface InvitationMessageValidation {
  canonical: string
  wordCount: number
  codePointCount: number
  reason: InvitationMessageReason | null
}

function parseContract<T>(schema: z.ZodType<T>, payload: unknown): T {
  try {
    const result = schema.safeParse(payload)
    if (result.success) return Object.freeze(result.data)
  } catch {
    // Response details can contain private values; expose only a stable client error.
  }
  throw new ApiError(200, 'invalidResponse')
}

function validateInvitationMessage(message: string): InvitationMessageValidation {
  const canonical = message.trim()
  const codePointCount = Array.from(canonical).length
  const wordCount = canonical.match(/\S+/gu)?.length ?? 0
  const reason =
    codePointCount > MAX_INVITATION_MESSAGE_CODE_POINTS
      ? 'INVITATION_MESSAGE_TOO_MANY_CODE_POINTS'
      : wordCount > MAX_INVITATION_MESSAGE_WORDS
        ? 'INVITATION_MESSAGE_TOO_MANY_WORDS'
        : null
  return { canonical, wordCount, codePointCount, reason }
}

const reasonErrorKeys: Readonly<Partial<Record<InvitationApiErrorReason, string>>> = {
  INVITATION_MESSAGE_TOO_MANY_WORDS: 'messageTooManyWords',
  INVITATION_MESSAGE_TOO_MANY_CODE_POINTS: 'messageTooManyCodePoints',
  INVITATION_SELF_NOT_ALLOWED: 'unavailable',
  INVITATION_SENDER_INELIGIBLE: 'eligibilityChanged',
  INVITATION_RECIPIENT_INELIGIBLE: 'recipientUnavailable',
  INVITATION_PENDING_LIMIT_REACHED: 'pendingLimit',
  INVITATION_PENDING_EXISTS: 'pendingExists',
  INVITATION_ACTIVE_PAIR_EXISTS: 'activeRelationship',
  INVITATION_ACCEPT_NOT_FOUND: 'stale',
  INVITATION_ACCEPT_EXPIRED: 'expired',
  INVITATION_ACCEPT_NOT_PENDING: 'stale',
  INVITATION_ACCEPT_RECIPIENT_INELIGIBLE: 'eligibilityChanged',
  INVITATION_ACCEPT_PARTICIPANT_INELIGIBLE: 'participantUnavailable',
  INVITATION_ACCEPT_OPPOSITE_TYPES_REQUIRED: 'typesChanged',
  INVITATION_ACCEPT_ACTIVE_PAIR_EXISTS: 'activeRelationship',
  INVITATION_ACCEPT_STATE_CONFLICT: 'stale',
  INVITATION_MUTATION_NOT_FOUND: 'stale',
  INVITATION_MUTATION_EXPIRED: 'expired',
  INVITATION_MUTATION_INVALID_STATE: 'stale',
}

function invitationErrorKey(error: unknown, action: InvitationAction): string {
  if (!(error instanceof ApiError)) return 'generic'
  if (error.reason) return reasonErrorKeys[error.reason as InvitationApiErrorReason] ?? 'generic'
  if (error.code === 'rateLimited') return 'rateLimited'
  if (error.code === 'forbidden') return 'verificationRequired'
  if (error.code === 'unauthorized') return 'sessionExpired'
  if (error.code === 'network') return 'network'
  if (error.code === 'validation') return action === 'send' ? 'validation' : 'stale'
  if (error.code === 'conflict' || error.code === 'notFound') return 'stale'
  return 'generic'
}

export {
  INVITATION_PAGE_SIZE,
  MAX_INVITATION_MESSAGE_CODE_POINTS,
  MAX_INVITATION_MESSAGE_WORDS,
  invitationErrorKey,
  parseContract,
  validateInvitationMessage,
  incomingInvitationListSchema,
  invitationAcceptResponseSchema,
  invitationCreateResponseSchema,
  invitationMutationResponseSchema,
  sentInvitationListSchema,
}
export type {
  IncomingInvitation,
  IncomingInvitationList,
  InvitationAcceptResponse,
  InvitationAction,
  InvitationCreateResponse,
  InvitationMessageReason,
  InvitationMessageValidation,
  InvitationMutationResponse,
  InvitationProfile,
  SentInvitation,
  SentInvitationList,
}
