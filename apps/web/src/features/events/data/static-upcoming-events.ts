import goOutDayImage from '@/features/events/assets/go-out-day.jpeg'
import halloweenImage from '@/features/events/assets/halloween.jpg'
import internationalDayImage from '@/features/events/assets/international-day.jpg'
import recruitmentImage from '@/features/events/assets/recruitment.jpg'
import scavengerHuntImage from '@/features/events/assets/scavenger-hunt.png'
import welcomeDayImage from '@/features/events/assets/welcome-day.png'
import type { EventSlider, EventSliderLocale } from '@/features/events/event-slider'

type LocalizedText = Readonly<Record<EventSliderLocale, string>>

interface StaticUpcomingEventDefinition {
  id: string
  imageUrl: string
  title: LocalizedText
  imageAlt: LocalizedText
}

// Transitional current-launch content. These event names and posters come from the
// project-owned legacy landing carousel; no schedule or location is invented here.
const staticUpcomingEventDefinitions = [
  {
    id: 'halloween',
    imageUrl: halloweenImage,
    title: { de: 'Halloween', en: 'Halloween' },
    imageAlt: { de: 'Poster zur Halloween-Veranstaltung', en: 'Halloween event poster' },
  },
  {
    id: 'grand-recruitment',
    imageUrl: recruitmentImage,
    title: { de: 'Grand Recruitment', en: 'Grand Recruitment' },
    imageAlt: { de: 'Poster zur Buddy-Rekrutierung', en: 'Buddy recruitment poster' },
  },
  {
    id: 'welcome-day',
    imageUrl: welcomeDayImage,
    title: { de: 'Welcome Day', en: 'Welcome Day' },
    imageAlt: { de: 'Poster zum Welcome Day', en: 'Welcome Day event poster' },
  },
  {
    id: 'scavenger-hunt',
    imageUrl: scavengerHuntImage,
    title: { de: 'Scavenger Hunt', en: 'Scavenger Hunt' },
    imageAlt: { de: 'Poster zur Scavenger Hunt', en: 'Scavenger Hunt event poster' },
  },
  {
    id: 'international-day',
    imageUrl: internationalDayImage,
    title: { de: 'International Day', en: 'International Day' },
    imageAlt: { de: 'Poster zum International Day', en: 'International Day event poster' },
  },
  {
    id: 'go-out-day',
    imageUrl: goOutDayImage,
    title: { de: 'Go Out Day', en: 'Go Out Day' },
    imageAlt: { de: 'Poster zum Go Out Day', en: 'Go Out Day event poster' },
  },
] as const satisfies readonly StaticUpcomingEventDefinition[]

function getStaticUpcomingEvents(locale: EventSliderLocale): EventSlider[] {
  return staticUpcomingEventDefinitions.map((event, sortOrder) => ({
    id: event.id,
    title: event.title[locale],
    description: null,
    imageUrl: event.imageUrl,
    imageAlt: event.imageAlt[locale],
    eventStartAt: null,
    eventEndAt: null,
    location: null,
    cta: null,
    sortOrder,
  }))
}

export { getStaticUpcomingEvents, staticUpcomingEventDefinitions }
export type { StaticUpcomingEventDefinition }
