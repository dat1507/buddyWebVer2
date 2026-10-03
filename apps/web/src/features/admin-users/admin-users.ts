import { z } from 'zod'

import { sessionClient } from '@/features/auth/session-client'
import { parseContract } from '@/features/matching/invitation'

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

type StudentType = z.infer<typeof adminProfileSummarySchema>['student_type']
type AdminUserSummary = Readonly<z.infer<typeof adminUserSummarySchema>>
type AdminUserList = Readonly<z.infer<typeof adminUserListSchema>>

interface AdminUserListRequest {
  page: number
  pageSize: number
  search: string
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

const adminUsersClient = {
  async readUsers(request: AdminUserListRequest): Promise<AdminUserList> {
    return parseContract(
      adminUserListSchema,
      await sessionClient.authenticatedJson(adminUserListPath(request), {
        signal: request.signal,
      }),
    )
  },
}

export { ADMIN_USERS_DEFAULT_PAGE_SIZE, adminUserListPath, adminUserListSchema, adminUsersClient }
export type { AdminUserList, AdminUserListRequest, AdminUserSummary, StudentType }
