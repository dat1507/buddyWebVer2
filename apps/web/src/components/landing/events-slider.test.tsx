import { fireEvent, render, screen } from '@testing-library/react'
import { beforeEach, describe, expect, it } from 'vitest'

import { EventsSlider } from '@/components/landing/events-slider'
import type { EventSlider } from '@/features/events/event-slider'
import i18n from '@/i18n'

const events: EventSlider[] = [
  {
    id: '11111111-1111-4111-8111-111111111111',
    title: 'Welcome Day',
    description: 'Meet the community.',
    imageUrl: 'https://cdn.example.com/welcome.webp',
    imageAlt: 'Students at Welcome Day',
    eventStartAt: null,
    eventEndAt: null,
    location: null,
    cta: null,
    sortOrder: 0,
  },
  {
    id: '22222222-2222-4222-8222-222222222222',
    title: 'International Day',
    description: null,
    imageUrl: 'https://cdn.example.com/international.webp',
    imageAlt: 'International Day',
    eventStartAt: null,
    eventEndAt: null,
    location: null,
    cta: null,
    sortOrder: 1,
  },
]

function renderSlider(result: readonly EventSlider[]) {
  return render(<EventsSlider events={result} />)
}

function setReducedMotion(matches: boolean) {
  Object.defineProperty(window, 'matchMedia', {
    configurable: true,
    value: (query: string) => ({
      matches,
      media: query,
      onchange: null,
      addEventListener: () => undefined,
      removeEventListener: () => undefined,
      addListener: () => undefined,
      removeListener: () => undefined,
      dispatchEvent: () => false,
    }),
  })
}

describe('EventsSlider', () => {
  beforeEach(async () => {
    setReducedMotion(false)
    await i18n.changeLanguage('en')
  })

  it('hides the complete section when the static dataset is empty', () => {
    const { container } = renderSlider([])

    expect(container).toBeEmptyDOMElement()
    expect(screen.queryByRole('heading', { name: 'Upcoming Events' })).not.toBeInTheDocument()
  })

  it('has no network error or retry UI in static mode', () => {
    renderSlider(events)

    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Try again' })).not.toBeInTheDocument()
  })

  it('renders typed static content and supports manual navigation', () => {
    renderSlider(events)

    expect(screen.getAllByText('Welcome Day').length).toBeGreaterThan(0)
    expect(screen.getAllByRole('img', { name: 'Students at Welcome Day' }).length).toBeGreaterThan(
      0,
    )
    expect(screen.getByText('Event 1 of 2')).toBeVisible()
    fireEvent.click(screen.getByRole('button', { name: 'Show next event' }))
    expect(screen.getByText('Event 2 of 2')).toBeVisible()
  })

  it('omits navigation controls and detail links for one promotional card', () => {
    renderSlider(events.slice(0, 1))

    expect(screen.getByText('Welcome Day')).toBeVisible()
    expect(screen.queryByRole('button', { name: 'Show next event' })).not.toBeInTheDocument()
    expect(screen.queryByRole('link')).not.toBeInTheDocument()
    expect(screen.getByText('Event 1 of 1')).toBeVisible()
  })

  it('keeps manual navigation usable when reduced motion is enabled', () => {
    setReducedMotion(true)
    renderSlider(events)

    screen.getAllByText('Welcome Day')
    const nextButton = screen.getByRole('button', { name: 'Show next event' })
    fireEvent.click(nextButton)
    expect(screen.getByText('Event 2 of 2')).toBeVisible()
    expect(nextButton).toBeEnabled()
    fireEvent.click(nextButton)
    expect(screen.getByText('Event 1 of 2')).toBeVisible()
  })
})
