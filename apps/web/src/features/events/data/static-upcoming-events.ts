import christmasImage from '@/features/events/assets/christmas.jpg'
import clubFair26Image from '@/features/events/assets/club-fair-26.jpg'
import experienceDayImage from '@/features/events/assets/experience-day.jpg'
import halloweenImage from '@/features/events/assets/halloween-new.jpg'
import recruitmentImage from '@/features/events/assets/recruitment-new.jpg'
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
    id: 'recruitment',
    imageUrl: recruitmentImage,
    title: { de: 'Recruitment', en: 'Recruitment' },
    imageAlt: { de: 'Poster zur Recruitment-Veranstaltung', en: 'Recruitment event poster' },
  },
  {
    id: 'club-fair-26',
    imageUrl: clubFair26Image,
    title: { de: 'Club Fair 26', en: 'Club Fair 26' },
    imageAlt: { de: 'Poster zur Club Fair 26', en: 'Club Fair 26 event poster' },
  },
  {
    id: 'experience-day',
    imageUrl: experienceDayImage,
    title: { de: 'Experience Day', en: 'Experience Day' },
    imageAlt: { de: 'Poster zum Experience Day', en: 'Experience Day event poster' },
  },
  {
    id: 'christmas',
    imageUrl: christmasImage,
    title: { de: 'Christmas', en: 'Christmas' },
    imageAlt: { de: 'Poster zur Weihnachtsveranstaltung', en: 'Christmas event poster' },
  },
  {
    id: 'halloween',
    imageUrl: halloweenImage,
    title: { de: 'Halloween', en: 'Halloween' },
    imageAlt: { de: 'Poster zur Halloween-Veranstaltung', en: 'Halloween event poster' },
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
