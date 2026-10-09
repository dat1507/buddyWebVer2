import { z } from 'zod'

import { sessionClient } from '@/features/auth/session-client'
import { parseContract } from '@/features/matching/invitation'
import { ApiError } from '@/lib/api'

const ADMIN_EVENTS_DEFAULT_PAGE_SIZE = 20
const eventStatusSchema = z.enum(['DRAFT', 'PUBLISHED', 'CANCELLED'])
const eventVisibilitySchema = z.enum(['PUBLIC', 'MEMBERS'])
const eventPhaseSchema = z.enum(['UPCOMING', 'ONGOING', 'COMPLETED'])
const awareDateTimeSchema = z.string().refine((value) => {
  if (!/(?:Z|[+-]\d{2}:\d{2})$/.test(value)) return false
  return !Number.isNaN(new Date(value).getTime())
})

const adminEventSchema = z
  .object({
    id: z.string().uuid(),
    title_en: z.string().min(1).max(120).nullable(),
    title_de: z.string().min(1).max(120).nullable(),
    description_en: z.string().min(1).max(10_000).nullable(),
    description_de: z.string().min(1).max(10_000).nullable(),
    start_date: awareDateTimeSchema.nullable(),
    end_date: awareDateTimeSchema.nullable(),
    timezone: z.string().min(1).max(255),
    location_en: z.string().min(1).max(200).nullable(),
    location_de: z.string().min(1).max(200).nullable(),
    category: z.string().min(1).max(80).nullable(),
    organizer: z.string().min(1).max(200).nullable(),
    registration_url: z.url().startsWith('https://').nullable(),
    cover_media_id: z.string().uuid().nullable(),
    status: eventStatusSchema,
    visibility: eventVisibilitySchema,
    phase: eventPhaseSchema.nullable(),
    registration_enabled: z.boolean(),
    max_participants: z.number().int().positive().nullable(),
    registration_deadline: awareDateTimeSchema.nullable(),
    published_at: awareDateTimeSchema.nullable(),
    version: z.number().int().positive(),
    created_at: awareDateTimeSchema,
    updated_at: awareDateTimeSchema,
  })
  .strict()

const adminEventListSchema = z
  .object({
    items: z.array(adminEventSchema),
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
      context.addIssue({ code: 'custom', message: 'Inconsistent admin Event page.' })
    }
  })

const adminEventMediaSchema = z
  .object({
    id: z.string().uuid(),
    event_id: z.string().uuid(),
    usage: z.literal('EVENT_COVER'),
    alt_en: z.string().min(1).max(200),
    alt_de: z.string().min(1).max(200),
    mime_type: z.enum(['image/jpeg', 'image/png', 'image/webp']),
    byte_size: z
      .number()
      .int()
      .positive()
      .max(5 * 1024 * 1024),
    width: z.number().int().positive().max(4096),
    height: z.number().int().positive().max(4096),
    sort_order: z.number().int().nonnegative(),
    processing_status: z.literal('READY'),
    created_at: awareDateTimeSchema,
    updated_at: awareDateTimeSchema,
  })
  .strict()

const eventCoverUploadResponseSchema = z
  .object({
    event: adminEventSchema,
    media: adminEventMediaSchema,
    cleanup_pending: z.boolean(),
  })
  .strict()

const eventMediaUrlSchema = z
  .object({
    id: z.string().uuid(),
    event_id: z.string().uuid(),
    url: z.url().startsWith('https://'),
    expires_in: z.number().int().min(1).max(300),
  })
  .strict()

type EventStatus = z.infer<typeof eventStatusSchema>
type EventVisibility = z.infer<typeof eventVisibilitySchema>
type EventPhase = z.infer<typeof eventPhaseSchema>
type AdminEvent = Readonly<z.infer<typeof adminEventSchema>>
type AdminEventList = Readonly<z.infer<typeof adminEventListSchema>>
type AdminEventMedia = Readonly<z.infer<typeof adminEventMediaSchema>>
type EventCoverUploadResponse = Readonly<z.infer<typeof eventCoverUploadResponseSchema>>
type EventMediaUrl = Readonly<z.infer<typeof eventMediaUrlSchema>>

interface EventDraftPayload {
  title_en: string | null
  title_de: string | null
  description_en: string | null
  description_de: string | null
  start_date: string | null
  end_date: string | null
  timezone: string
  location_en: string | null
  location_de: string | null
  category: string | null
  organizer: string | null
  registration_url: string | null
  visibility: EventVisibility
  registration_enabled: boolean
  max_participants: number | null
  registration_deadline: string | null
}

interface EventCoverUploadInput {
  eventId: string
  version: number
  altEn: string
  altDe: string
  file: File
}

interface EventStatusUpdateInput {
  eventId: string
  version: number
  status: EventStatus
}

interface AdminEventListRequest {
  page: number
  pageSize: number
  search: string
  status: EventStatus | null
  visibility: EventVisibility | null
  phase: EventPhase | null
  from: string | null
  to: string | null
  signal?: AbortSignal
}

function adminEventListPath(request: AdminEventListRequest): string {
  const params = new URLSearchParams({
    page: String(request.page),
    page_size: String(request.pageSize),
  })
  const search = request.search.trim()
  if (search) params.set('search', search)
  if (request.status) params.set('status', request.status)
  if (request.visibility) params.set('visibility', request.visibility)
  if (request.phase) params.set('phase', request.phase)
  if (request.from && request.to) {
    params.set('from', request.from)
    params.set('to', request.to)
  }
  return `/admin/events?${params}`
}

const adminEventsClient = {
  async readEvents(request: AdminEventListRequest): Promise<AdminEventList> {
    return parseContract(
      adminEventListSchema,
      await sessionClient.authenticatedJson(adminEventListPath(request), {
        signal: request.signal,
      }),
    )
  },

  async readEvent(eventId: string, signal?: AbortSignal): Promise<AdminEvent> {
    const event = parseContract(
      adminEventSchema,
      await sessionClient.authenticatedJson(`/admin/events/${encodeURIComponent(eventId)}`, {
        signal,
      }),
    )
    if (event.id !== eventId) throw new ApiError(200, 'invalidResponse')
    return event
  },

  async createDraft(payload: EventDraftPayload): Promise<AdminEvent> {
    return parseContract(
      adminEventSchema,
      await sessionClient.authenticatedJson('/admin/events', {
        method: 'POST',
        body: payload,
      }),
    )
  },

  async updateEvent(
    eventId: string,
    payload: EventDraftPayload & { version: number },
  ): Promise<AdminEvent> {
    const event = parseContract(
      adminEventSchema,
      await sessionClient.authenticatedJson(`/admin/events/${encodeURIComponent(eventId)}`, {
        method: 'PUT',
        body: payload,
      }),
    )
    if (event.id !== eventId) throw new ApiError(200, 'invalidResponse')
    return event
  },

  async uploadCover(input: EventCoverUploadInput): Promise<EventCoverUploadResponse> {
    const formData = new FormData()
    formData.append('version', String(input.version))
    formData.append('alt_en', input.altEn.trim())
    formData.append('alt_de', input.altDe.trim())
    formData.append('file', input.file, input.file.name)
    const result = parseContract(
      eventCoverUploadResponseSchema,
      await sessionClient.authenticatedJson(
        `/admin/events/${encodeURIComponent(input.eventId)}/media`,
        { method: 'POST', formData },
      ),
    )
    if (result.event.id !== input.eventId || result.media.event_id !== input.eventId) {
      throw new ApiError(200, 'invalidResponse')
    }
    return result
  },

  async setStatus(input: EventStatusUpdateInput): Promise<AdminEvent> {
    const event = parseContract(
      adminEventSchema,
      await sessionClient.authenticatedJson(
        `/admin/events/${encodeURIComponent(input.eventId)}/status`,
        {
          method: 'PATCH',
          body: { version: input.version, status: input.status },
        },
      ),
    )
    if (event.id !== input.eventId) throw new ApiError(200, 'invalidResponse')
    return event
  },

  async readCoverUrl(
    eventId: string,
    mediaId: string,
    signal?: AbortSignal,
  ): Promise<EventMediaUrl> {
    const result = parseContract(
      eventMediaUrlSchema,
      await sessionClient.authenticatedJson(
        `/events/${encodeURIComponent(eventId)}/media/${encodeURIComponent(mediaId)}/url`,
        { signal },
      ),
    )
    if (result.event_id !== eventId || result.id !== mediaId) {
      throw new ApiError(200, 'invalidResponse')
    }
    return result
  },
}

export {
  ADMIN_EVENTS_DEFAULT_PAGE_SIZE,
  adminEventListPath,
  adminEventListSchema,
  adminEventMediaSchema,
  adminEventSchema,
  adminEventsClient,
  eventCoverUploadResponseSchema,
  eventMediaUrlSchema,
  eventPhaseSchema,
  eventStatusSchema,
  eventVisibilitySchema,
}
export type {
  AdminEvent,
  AdminEventList,
  AdminEventListRequest,
  AdminEventMedia,
  EventCoverUploadInput,
  EventCoverUploadResponse,
  EventDraftPayload,
  EventMediaUrl,
  EventPhase,
  EventStatus,
  EventStatusUpdateInput,
  EventVisibility,
}
