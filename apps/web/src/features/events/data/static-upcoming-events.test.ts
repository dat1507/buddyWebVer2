import { describe, expect, it } from 'vitest'

import {
  getStaticUpcomingEvents,
  staticUpcomingEventDefinitions,
} from '@/features/events/data/static-upcoming-events'

describe('temporary static Upcoming Events data', () => {
  it('uses bundled project assets and promotional-only content', () => {
    const events = getStaticUpcomingEvents('en')

    expect(events).toHaveLength(6)
    expect(events.map((event) => event.id)).toEqual([
      'halloween',
      'grand-recruitment',
      'welcome-day',
      'scavenger-hunt',
      'international-day',
      'go-out-day',
    ])
    expect(events.every((event) => event.imageUrl.length > 0)).toBe(true)
    expect(events.every((event) => event.cta === null)).toBe(true)
    expect(events.every((event) => event.eventStartAt === null && event.eventEndAt === null)).toBe(
      true,
    )
    expect(events.every((event) => event.location === null)).toBe(true)
  })

  it('localizes poster alternative text without changing the static source order', () => {
    const english = getStaticUpcomingEvents('en')
    const german = getStaticUpcomingEvents('de')

    expect(staticUpcomingEventDefinitions).toHaveLength(english.length)
    expect(german.map((event) => event.id)).toEqual(english.map((event) => event.id))
    expect(german[0].imageAlt).toBe('Poster zur Halloween-Veranstaltung')
    expect(english[0].imageAlt).toBe('Halloween event poster')
  })
})
