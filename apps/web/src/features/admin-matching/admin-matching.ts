import { z } from 'zod'

import { sessionClient } from '@/features/auth/session-client'
import { invitationProfileSchema, parseContract } from '@/features/matching/invitation'
import type { CatalogLocale } from '@/features/profile/profile-catalog'

const ADMIN_MATCHING_DEFAULT_PAGE_SIZE = 20

const studentTypeSchema = z.enum(['VIETNAMESE', 'INTERNATIONAL'])

const invitationStateCountsSchema = z
  .object({
    pending: z.number().int().nonnegative(),
    accepted: z.number().int().nonnegative(),
    declined: z.number().int().nonnegative(),
    cancelled: z.number().int().nonnegative(),
    expired: z.number().int().nonnegative(),
  })
  .strict()

const adminMatchingStatsSchema = z
  .object({
    participant_count: z.number().int().nonnegative(),
    verified_participant_count: z.number().int().nonnegative(),
    active_match_count: z.number().int().nonnegative(),
    zero_buddy_participant_count: z.number().int().nonnegative(),
    invitations: invitationStateCountsSchema,
  })
  .strict()

const adminMatchingParticipantSchema = z
  .object({
    profile_id: z.string().uuid(),
    display_name: z.string().max(80).nullable(),
    student_type: studentTypeSchema.nullable(),
    is_active: z.boolean(),
    email_verified: z.boolean(),
    matching_opt_in: z.boolean(),
    buddy_count: z.number().int().nonnegative(),
  })
  .strict()

const adminMatchingParticipantListSchema = z
  .object({
    items: z.array(adminMatchingParticipantSchema),
    page: z.number().int().min(1),
    page_size: z.number().int().min(1).max(50),
    total: z.number().int().nonnegative(),
    total_pages: z.number().int().nonnegative(),
  })
  .strict()
  .superRefine((value, context) => {
    const expectedPages = value.total === 0 ? 0 : Math.ceil(value.total / value.page_size)
    const identifiers = value.items.map(({ profile_id }) => profile_id)
    if (
      value.items.length > value.page_size ||
      value.total_pages !== expectedPages ||
      (value.total_pages > 0 && value.page > value.total_pages) ||
      new Set(identifiers).size !== identifiers.length
    ) {
      context.addIssue({ code: 'custom', message: 'Inconsistent participant page.' })
    }
  })

const adminMatchingParticipantDetailSchema = z
  .object({
    profile: invitationProfileSchema,
    is_active: z.boolean(),
    email_verified: z.boolean(),
    matching_opt_in: z.boolean(),
    buddy_count: z.number().int().nonnegative(),
  })
  .strict()

type StudentType = z.infer<typeof studentTypeSchema>
type AdminMatchingStats = Readonly<z.infer<typeof adminMatchingStatsSchema>>
type AdminMatchingParticipant = Readonly<z.infer<typeof adminMatchingParticipantSchema>>
type AdminMatchingParticipantList = Readonly<z.infer<typeof adminMatchingParticipantListSchema>>
type AdminMatchingParticipantDetail = Readonly<z.infer<typeof adminMatchingParticipantDetailSchema>>

interface AdminMatchingParticipantRequest {
  page: number
  pageSize: number
  studentType: StudentType | null
  verified: boolean | null
  zeroBuddiesOnly: boolean
  signal?: AbortSignal
}

interface AdminMatchingParticipantDetailRequest {
  profileId: string
  locale: CatalogLocale
  signal?: AbortSignal
}

function participantListPath(request: AdminMatchingParticipantRequest): string {
  const search = new URLSearchParams({
    page: String(request.page),
    page_size: String(request.pageSize),
  })
  if (request.studentType) search.set('student_type', request.studentType)
  if (request.verified !== null) search.set('verified', String(request.verified))
  if (request.zeroBuddiesOnly) search.set('zero_buddies_only', 'true')
  return `/admin/matching/participants?${search}`
}

const adminMatchingClient = {
  async readStats(signal?: AbortSignal): Promise<AdminMatchingStats> {
    return parseContract(
      adminMatchingStatsSchema,
      await sessionClient.authenticatedJson('/admin/matching/stats', { signal }),
    )
  },
  async readParticipants(
    request: AdminMatchingParticipantRequest,
  ): Promise<AdminMatchingParticipantList> {
    return parseContract(
      adminMatchingParticipantListSchema,
      await sessionClient.authenticatedJson(participantListPath(request), {
        signal: request.signal,
      }),
    )
  },
  async readParticipantDetail({
    profileId,
    locale,
    signal,
  }: AdminMatchingParticipantDetailRequest): Promise<AdminMatchingParticipantDetail> {
    const search = new URLSearchParams({ locale })
    return parseContract(
      adminMatchingParticipantDetailSchema,
      await sessionClient.authenticatedJson(
        `/admin/matching/participants/${encodeURIComponent(profileId)}?${search}`,
        { signal },
      ),
    )
  },
}

export {
  ADMIN_MATCHING_DEFAULT_PAGE_SIZE,
  adminMatchingClient,
  adminMatchingParticipantDetailSchema,
  adminMatchingParticipantListSchema,
  adminMatchingStatsSchema,
  participantListPath,
}
export type {
  AdminMatchingParticipant,
  AdminMatchingParticipantDetail,
  AdminMatchingParticipantDetailRequest,
  AdminMatchingParticipantList,
  AdminMatchingParticipantRequest,
  AdminMatchingStats,
  StudentType,
}
