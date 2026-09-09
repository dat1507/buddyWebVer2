import { parsePublicEventSliders, type EventSliderLocale } from '@/features/events/event-slider'
import type { EventSliderRepository } from '@/features/events/repositories/event-slider-repository'
import { getJson } from '@/lib/api'

const apiEventSliderRepository: EventSliderRepository = {
  async listPublished(locale: EventSliderLocale, signal?: AbortSignal) {
    const payload = await getJson(`/event-sliders?locale=${encodeURIComponent(locale)}`, signal)

    return parsePublicEventSliders(payload)
  },
}

export { apiEventSliderRepository }
