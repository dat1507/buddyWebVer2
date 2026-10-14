import { z } from 'zod'

import { parseContract } from '@/features/matching/invitation'
import { ApiError, getJson } from '@/lib/api'

const eventLocaleSchema = z.enum(['en', 'de'])
const legacyEventVisibilitySchema = z.enum(['PUBLIC', 'MEMBERS'])
const awareDateTimeSchema = z.string().refine((value) => {
  if (!/(?:Z|[+-]\d{2}:\d{2})$/.test(value)) return false
  return !Number.isNaN(new Date(value).getTime())
})
const httpsUrlSchema = z.url().refine((value) => new URL(value).protocol === 'https:')

const publicEventCoverSchema = z
  .object({
    url: httpsUrlSchema,
    alt_text: z.string().min(1).max(200),
    mime_type: z.enum(['image/jpeg', 'image/png', 'image/webp']),
    width: z.number().int().positive().max(4096),
    height: z.number().int().positive().max(4096),
    expires_in: z.number().int().min(1).max(300),
  })
  .strict()

const publicEventSchema = z
  .object({
    id: z.string().uuid(),
    locale: eventLocaleSchema,
    title: z.string().min(1).max(120),
    description: z.string().min(1).max(10_000),
    start_date: awareDateTimeSchema.nullable(),
    end_date: awareDateTimeSchema.nullable(),
    timezone: z.string().min(1).max(255),
    location: z.string().min(1).max(200).nullable(),
    category: z.string().min(1).max(80).nullable(),
    organizer: z.string().min(1).max(200).nullable(),
    registration_url: httpsUrlSchema.nullable(),
    registration_enabled: z.boolean(),
    registration_deadline: awareDateTimeSchema.nullable(),
    status: z.enum(['PUBLISHED', 'CANCELLED']),
    // Old API revisions can still emit this field during a rolling deploy. It
    // is accepted at the wire boundary but removed from the public Event model.
    visibility: legacyEventVisibilitySchema.optional(),
    phase: z.enum(['UPCOMING', 'ONGOING', 'COMPLETED']).nullable(),
    cover: publicEventCoverSchema.nullable(),
  })
  .strict()
  .superRefine((event, context) => {
    if (
      event.start_date &&
      event.end_date &&
      new Date(event.end_date).getTime() <= new Date(event.start_date).getTime()
    ) {
      context.addIssue({ code: 'custom', message: 'Event end must follow its start.' })
    }
  })
  .transform(({ visibility, ...event }) => {
    void visibility
    return event
  })

const publicEventListSchema = z
  .object({
    items: z.array(publicEventSchema),
    page: z.number().int().min(1),
    page_size: z.number().int().min(1).max(100),
    total: z.number().int().nonnegative(),
    total_pages: z.number().int().nonnegative(),
  })
  .strict()
  .superRefine((value, context) => {
    const expectedPages = value.total === 0 ? 0 : Math.ceil(value.total / value.page_size)
    if (
      value.items.length > value.page_size ||
      value.items.length > value.total ||
      value.total_pages !== expectedPages ||
      new Set(value.items.map(({ id }) => id)).size !== value.items.length
    ) {
      context.addIssue({ code: 'custom', message: 'Inconsistent public Event page.' })
    }
  })

type EventLocale = z.infer<typeof eventLocaleSchema>
type PublicEvent = Readonly<z.infer<typeof publicEventSchema>>
type PublicEventCover = Readonly<z.infer<typeof publicEventCoverSchema>>
type PublicEventList = Readonly<z.infer<typeof publicEventListSchema>>

const publicEventsClient = {
  async readEvents(locale: EventLocale, signal?: AbortSignal): Promise<PublicEventList> {
    return parseContract(
      publicEventListSchema,
      await getJson(`/events?locale=${encodeURIComponent(locale)}&page=1&page_size=100`, signal),
    )
  },

  async readEvent(
    eventId: string,
    locale: EventLocale,
    signal?: AbortSignal,
  ): Promise<PublicEvent> {
    const event = parseContract(
      publicEventSchema,
      await getJson(
        `/events/${encodeURIComponent(eventId)}?locale=${encodeURIComponent(locale)}`,
        signal,
      ),
    )
    if (event.id !== eventId || event.locale !== locale) {
      throw new ApiError(200, 'invalidResponse')
    }
    return event
  },
}

export {
  eventLocaleSchema,
  publicEventCoverSchema,
  publicEventListSchema,
  publicEventSchema,
  publicEventsClient,
}
export type { EventLocale, PublicEvent, PublicEventCover, PublicEventList }
