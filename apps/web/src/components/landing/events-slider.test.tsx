import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen } from '@testing-library/react'
import { beforeEach, describe, expect, it } from 'vitest'

import { EventsSlider } from '@/components/landing/events-slider'
import type { EventSlider } from '@/features/events/event-slider'
import type { EventSliderRepository } from '@/features/events/repositories/event-slider-repository'
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

function renderSlider(repository: EventSliderRepository) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0 } },
  })

  return render(
    <QueryClientProvider client={queryClient}>
      <EventsSlider repository={repository} />
    </QueryClientProvider>,
  )
}

function repositoryReturning(result: EventSlider[]): EventSliderRepository {
  return { listPublished: async () => result }
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

  it('shows a loading state while the repository is pending', () => {
    renderSlider({ listPublished: () => new Promise(() => undefined) })

    expect(screen.getByRole('status')).toHaveTextContent('Loading upcoming events')
  })

  it('shows the localized empty state', async () => {
    await i18n.changeLanguage('de')
    renderSlider(repositoryReturning([]))

    expect(
      await screen.findByText('Derzeit gibt es keine bevorstehenden Veranstaltungen.'),
    ).toBeVisible()
  })

  it('allows a failed request to be retried', async () => {
    let requestCount = 0
    const repository: EventSliderRepository = {
      listPublished: async () => {
        requestCount += 1
        if (requestCount === 1) throw new Error('Unavailable')
        return events
      },
    }
    renderSlider(repository)

    expect(await screen.findByRole('alert')).toBeVisible()
    fireEvent.click(screen.getByRole('button', { name: 'Try again' }))
    expect((await screen.findAllByText('Welcome Day')).length).toBeGreaterThan(0)
  })

  it('renders API-shaped content and supports manual navigation', async () => {
    renderSlider(repositoryReturning(events))

    expect((await screen.findAllByText('Welcome Day')).length).toBeGreaterThan(0)
    expect(screen.getByText('Event 1 of 2')).toBeVisible()
    fireEvent.click(screen.getByRole('button', { name: 'Show next event' }))
    expect(screen.getByText('Event 2 of 2')).toBeVisible()
  })

  it('omits navigation controls for a single event', async () => {
    renderSlider(repositoryReturning(events.slice(0, 1)))

    expect(await screen.findByText('Welcome Day')).toBeVisible()
    expect(screen.queryByRole('button', { name: 'Show next event' })).not.toBeInTheDocument()
    expect(screen.getByText('Event 1 of 1')).toBeVisible()
  })

  it('keeps manual navigation usable when reduced motion is enabled', async () => {
    setReducedMotion(true)
    renderSlider(repositoryReturning(events))

    await screen.findAllByText('Welcome Day')
    const nextButton = screen.getByRole('button', { name: 'Show next event' })
    fireEvent.click(nextButton)
    expect(screen.getByText('Event 2 of 2')).toBeVisible()
    expect(nextButton).toBeEnabled()
    fireEvent.click(nextButton)
    expect(screen.getByText('Event 1 of 2')).toBeVisible()
  })
})
