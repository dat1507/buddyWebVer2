import { getStaticUpcomingEvents } from '@/features/events/data/static-upcoming-events'
import type { EventSliderRepository } from '@/features/events/repositories/event-slider-repository'

const mockEventSliderRepository: EventSliderRepository = {
  async listPublished(locale, signal) {
    if (signal?.aborted) {
      throw new DOMException('The request was aborted', 'AbortError')
    }

    return Promise.resolve(getStaticUpcomingEvents(locale))
  },
}

export { mockEventSliderRepository }
