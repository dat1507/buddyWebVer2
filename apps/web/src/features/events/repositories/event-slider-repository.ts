import type { EventSlider, EventSliderLocale } from '@/features/events/event-slider'

interface EventSliderRepository {
  listPublished(locale: EventSliderLocale, signal?: AbortSignal): Promise<EventSlider[]>
}

export type { EventSliderRepository }
