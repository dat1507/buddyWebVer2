import { z } from 'zod'

import { parseContract } from '@/features/matching/invitation'
import { ApiError, getJson } from '@/lib/api'

const eventLocaleSchema = z.enum(['en', 'de'])
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
    start_date: awareDateTimeSchema,
    end_date: awareDateTimeSchema,
    timezone: z.string().min(1).max(255),
    location: z.string().min(1).max(200),
    category: z.string().min(1).max(80).nullable(),
    organizer: z.string().min(1).max(200).nullable(),
    registration_url: httpsUrlSchema.nullable(),
    registration_enabled: z.boolean(),
    registration_deadline: awareDateTimeSchema.nullable(),
    status: z.enum(['PUBLISHED', 'CANCELLED']),
    visibility: z.enum(['PUBLIC', 'MEMBERS']),
    phase: z.enum(['UPCOMING', 'ONGOING', 'COMPLETED']),
    cover: publicEventCoverSchema.nullable(),
  })
  .strict()
  .superRefine((event, context) => {
    if (new Date(event.end_date).getTime() <= new Date(event.start_date).getTime()) {
      context.addIssue({ code: 'custom', message: 'Event end must follow its start.' })
    }
  })

type EventLocale = z.infer<typeof eventLocaleSchema>
type PublicEvent = Readonly<z.infer<typeof publicEventSchema>>
type PublicEventCover = Readonly<z.infer<typeof publicEventCoverSchema>>

const publicEventsClient = {
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

export { eventLocaleSchema, publicEventCoverSchema, publicEventSchema, publicEventsClient }
export type { EventLocale, PublicEvent, PublicEventCover }
