import { z } from 'zod'

const httpsUrlSchema = z
  .string()
  .url()
  .refine((value) => new URL(value).protocol === 'https:', {
    message: 'Expected an HTTPS URL',
  })

const ctaSchema = z
  .object({
    label: z.string().min(1).max(40),
    href: z
      .string()
      .refine(
        (value) =>
          value.startsWith('/') || value.startsWith('#') || httpsUrlSchema.safeParse(value).success,
        { message: 'Expected a relative path, hash, or HTTPS URL' },
      ),
  })
  .nullable()

const publicEventSliderApiSchema = z.object({
  id: z.string().uuid(),
  title: z.string().min(1).max(120),
  description: z.string().max(500).nullable(),
  image_url: httpsUrlSchema,
  image_alt: z.string().min(1).max(200),
  event_start_at: z.string().datetime({ offset: true }).nullable(),
  event_end_at: z.string().datetime({ offset: true }).nullable(),
  location: z.string().max(200).nullable(),
  cta: ctaSchema,
  sort_order: z.number().int().nonnegative(),
})

const publicEventSliderListSchema = z.array(publicEventSliderApiSchema)

type EventSliderLocale = 'de' | 'en'

interface EventSlider {
  id: string
  title: string
  description: string | null
  imageUrl: string
  imageAlt: string
  eventStartAt: string | null
  eventEndAt: string | null
  location: string | null
  cta: { label: string; href: string } | null
  sortOrder: number
}

function parsePublicEventSliders(payload: unknown): EventSlider[] {
  return publicEventSliderListSchema.parse(payload).map((slider) => ({
    id: slider.id,
    title: slider.title,
    description: slider.description,
    imageUrl: slider.image_url,
    imageAlt: slider.image_alt,
    eventStartAt: slider.event_start_at,
    eventEndAt: slider.event_end_at,
    location: slider.location,
    cta: slider.cta,
    sortOrder: slider.sort_order,
  }))
}

export { parsePublicEventSliders, publicEventSliderApiSchema }
export type { EventSlider, EventSliderLocale }
