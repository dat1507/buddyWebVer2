import type { EventSliderRepository } from '@/features/events/repositories/event-slider-repository'
import { apiEventSliderRepository } from '@/features/events/repositories/api-event-slider-repository'

const shouldUseDevelopmentMock =
  import.meta.env.DEV && import.meta.env.VITE_EVENT_SLIDER_USE_MOCKS !== 'false'

const eventSliderRepository: EventSliderRepository = {
  async listPublished(locale, signal) {
    if (shouldUseDevelopmentMock) {
      const { mockEventSliderRepository } =
        await import('@/features/events/mocks/mock-event-slider-repository')

      return mockEventSliderRepository.listPublished(locale, signal)
    }

    return apiEventSliderRepository.listPublished(locale, signal)
  },
}

export { eventSliderRepository }
