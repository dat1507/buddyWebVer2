import { z } from 'zod'

import { sessionClient } from '@/features/auth/session-client'
import { parseContract } from '@/features/matching/invitation'
import { profilePhotoSchema } from '@/features/profile/profile-photo'
import { ApiError } from '@/lib/api'

const ADMIN_USERS_DEFAULT_PAGE_SIZE = 20

const awareDateTimeSchema = z.string().refine((value) => {
  if (!/(?:Z|[+-]\d{2}:\d{2})$/.test(value)) return false
  return !Number.isNaN(new Date(value).getTime())
})

const adminProfileSummarySchema = z
  .object({
    id: z.string().uuid(),
    full_name: z.string().max(120).nullable(),
    display_name: z.string().max(80).nullable(),
    student_type: z.enum(['VIETNAMESE', 'INTERNATIONAL']).nullable(),
  })
  .strict()

const adminUserSummarySchema = z
  .object({
    id: z.string().uuid(),
    email: z.string().min(1).max(320),
    role: z.literal('USER'),
    is_active: z.boolean(),
    email_verified: z.boolean(),
    created_at: awareDateTimeSchema,
    profile: adminProfileSummarySchema.nullable(),
  })
  .strict()

const adminUserListSchema = z
  .object({
    items: z.array(adminUserSummarySchema),
    page: z.number().int().min(1),
    page_size: z.number().int().min(1).max(100),
    total: z.number().int().nonnegative(),
    total_pages: z.number().int().nonnegative(),
  })
  .strict()
  .superRefine((value, context) => {
    const expectedPages = value.total === 0 ? 0 : Math.ceil(value.total / value.page_size)
    const identifiers = value.items.map(({ id }) => id)
    if (
      value.items.length > value.page_size ||
      value.items.length > value.total ||
      value.total_pages !== expectedPages ||
      new Set(identifiers).size !== identifiers.length
    ) {
      context.addIssue({ code: 'custom', message: 'Inconsistent admin user page.' })
    }
  })

const isoDateSchema = z
  .string()
  .regex(/^\d{4}-\d{2}-\d{2}$/)
  .refine((value) => {
    const parsed = new Date(`${value}T00:00:00.000Z`)
    return !Number.isNaN(parsed.getTime()) && parsed.toISOString().startsWith(value)
  })

const adminProfileDetailSchema = adminProfileSummarySchema
  .extend({
    nationality: z.string().nullable(),
    major: z.string().nullable(),
    study_year: z.number().int().min(1).max(10).nullable(),
    bio: z.string().max(500).nullable(),
    home_university: z.string().nullable(),
    arrival_date: isoDateSchema.nullable(),
    departure_date: isoDateSchema.nullable(),
    matching_opt_in: z.boolean(),
    onboarding_completed_at: awareDateTimeSchema.nullable(),
    avatar: profilePhotoSchema.strict().nullable(),
  })
  .strict()

const adminUserDetailSchema = adminUserSummarySchema
  .extend({ profile: adminProfileDetailSchema.nullable() })
  .strict()

type StudentType = z.infer<typeof adminProfileSummarySchema>['student_type']
type AdminUserSummary = Readonly<z.infer<typeof adminUserSummarySchema>>
type AdminUserList = Readonly<z.infer<typeof adminUserListSchema>>
type AdminUserDetail = Readonly<z.infer<typeof adminUserDetailSchema>>

interface AdminUserListRequest {
  page: number
  pageSize: number
  search: string
  signal?: AbortSignal
}

interface AdminUserDetailRequest {
  userId: string
  signal?: AbortSignal
}

function adminUserListPath(request: AdminUserListRequest): string {
  const params = new URLSearchParams({
    page: String(request.page),
    page_size: String(request.pageSize),
  })
  const search = request.search.trim()
  if (search) params.set('search', search)
  return `/admin/users?${params}`
}

function adminUserDetailPath(userId: string): string {
  return `/admin/users/${encodeURIComponent(userId)}`
}

const adminUsersClient = {
  async readUsers(request: AdminUserListRequest): Promise<AdminUserList> {
    return parseContract(
      adminUserListSchema,
      await sessionClient.authenticatedJson(adminUserListPath(request), {
        signal: request.signal,
      }),
    )
  },
  async readUserDetail({ userId, signal }: AdminUserDetailRequest): Promise<AdminUserDetail> {
    const detail = parseContract(
      adminUserDetailSchema,
      await sessionClient.authenticatedJson(adminUserDetailPath(userId), { signal }),
    )
    if (detail.id !== userId) throw new ApiError(200, 'invalidResponse')
    return detail
  },
}

export {
  ADMIN_USERS_DEFAULT_PAGE_SIZE,
  adminUserDetailPath,
  adminUserDetailSchema,
  adminUserListPath,
  adminUserListSchema,
  adminUsersClient,
}
export type {
  AdminUserDetail,
  AdminUserDetailRequest,
  AdminUserList,
  AdminUserListRequest,
  AdminUserSummary,
  StudentType,
}
