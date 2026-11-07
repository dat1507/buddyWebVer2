import { z } from 'zod'

import { sessionClient } from '@/features/auth/session-client'
import { parseContract } from '@/features/matching/invitation'

export const auditCategories = [
  'events',
  'recaps',
  'users',
  'matching',
  'semesters',
  'other',
] as const
export const auditPeriods = ['today', 'week', 'month', 'custom'] as const
const status = z.enum(['DRAFT', 'PUBLISHED', 'CANCELLED', 'ARCHIVED']).nullable()

const activity = z
  .object({
    id: z.uuid(),
    created_at: z.iso.datetime({ offset: true }),
    admin_id: z.uuid(),
    admin_email: z.string().nullable(),
    action: z.string(),
    category: z.enum(auditCategories),
    resource_type: z.enum([
      'event',
      'recap',
      'student_profile',
      'profile_photo',
      'semester_operation',
      'other',
    ]),
    resource_id: z.uuid().nullable(),
    before_status: status,
    after_status: status,
  })
  .strict()

const auditPage = z
  .object({
    items: z.array(activity).max(100),
    page: z.number().int().positive(),
    page_size: z.number().int().min(1).max(100),
    total: z.number().int().nonnegative(),
    total_pages: z.number().int().nonnegative(),
  })
  .strict()

const actor = z.object({ id: z.uuid(), email: z.string() }).strict()
const actorPage = z.object({ items: z.array(actor).max(100), has_more: z.boolean() }).strict()

export type AuditActivity = z.infer<typeof activity>
export type AuditActor = z.infer<typeof actor>
export type AuditCategory = (typeof auditCategories)[number]
export type AuditPeriod = (typeof auditPeriods)[number]

export const adminAuditClient = {
  async list(params: URLSearchParams, signal: AbortSignal) {
    return parseContract(
      auditPage,
      await sessionClient.authenticatedJson('/admin/audit-logs?' + params, { signal }),
    )
  },
  async actors(page: number, signal: AbortSignal) {
    return parseContract(
      actorPage,
      await sessionClient.authenticatedJson('/admin/audit-logs/actors?page=' + page, { signal }),
    )
  },
}
