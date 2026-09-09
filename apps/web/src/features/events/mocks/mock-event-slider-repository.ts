import goOutDayImage from '@/features/events/mocks/assets/go-out-day.jpeg'
import halloweenImage from '@/features/events/mocks/assets/halloween.jpg'
import internationalDayImage from '@/features/events/mocks/assets/international-day.jpg'
import recruitmentImage from '@/features/events/mocks/assets/recruitment.jpg'
import scavengerHuntImage from '@/features/events/mocks/assets/scavenger-hunt.png'
import welcomeDayImage from '@/features/events/mocks/assets/welcome-day.png'
import type { EventSlider, EventSliderLocale } from '@/features/events/event-slider'
import type { EventSliderRepository } from '@/features/events/repositories/event-slider-repository'

const mockSlides = [
  {
    id: 'b1d91f8c-698d-4cca-b523-3bc55c2a5ad1',
    imageUrl: halloweenImage,
    title: { de: 'Halloween', en: 'Halloween' },
    imageAlt: { de: 'Poster zur Halloween-Veranstaltung', en: 'Halloween event poster' },
  },
  {
    id: '8f4ffb20-81c3-4214-aa60-2eb670b96e75',
    imageUrl: recruitmentImage,
    title: { de: 'Recruitment', en: 'Recruitment' },
    imageAlt: { de: 'Poster zur Buddy-Rekrutierung', en: 'Buddy recruitment poster' },
  },
  {
    id: '839345e0-d088-49d4-b616-fc4ed0c96a3b',
    imageUrl: welcomeDayImage,
    title: { de: 'Welcome Day', en: 'Welcome Day' },
    imageAlt: { de: 'Poster zum Welcome Day', en: 'Welcome Day event poster' },
  },
  {
    id: '5bc7de35-094a-4fe7-85ce-c84f589ca72e',
    imageUrl: scavengerHuntImage,
    title: { de: 'Scavenger Hunt', en: 'Scavenger Hunt' },
    imageAlt: { de: 'Poster zur Scavenger Hunt', en: 'Scavenger Hunt event poster' },
  },
  {
    id: '5df8eedc-209e-4423-a30f-5e5a5f9e432b',
    imageUrl: internationalDayImage,
    title: { de: 'International Day', en: 'International Day' },
    imageAlt: { de: 'Poster zum International Day', en: 'International Day event poster' },
  },
  {
    id: '04cf9bf8-dad5-47b8-838b-e65801fd6f95',
    imageUrl: goOutDayImage,
    title: { de: 'Go Out Day', en: 'Go Out Day' },
    imageAlt: { de: 'Poster zum Go Out Day', en: 'Go Out Day event poster' },
  },
] as const

function createLocalizedMockSliders(locale: EventSliderLocale): EventSlider[] {
  return mockSlides.map((slide, sortOrder) => ({
    id: slide.id,
    title: slide.title[locale],
    description: null,
    imageUrl: slide.imageUrl,
    imageAlt: slide.imageAlt[locale],
    eventStartAt: null,
    eventEndAt: null,
    location: null,
    cta: null,
    sortOrder,
  }))
}

const mockEventSliderRepository: EventSliderRepository = {
  async listPublished(locale, signal) {
    if (signal?.aborted) {
      throw new DOMException('The request was aborted', 'AbortError')
    }

    return Promise.resolve(createLocalizedMockSliders(locale))
  },
}

export { mockEventSliderRepository }
