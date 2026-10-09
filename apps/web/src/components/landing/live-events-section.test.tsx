import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { LiveEventsSection } from '@/components/landing/live-events-section'
import type { EventSlider } from '@/features/events/event-slider'
import type { EventSliderRepository } from '@/features/events/repositories/event-slider-repository'
import i18n from '@/i18n'

const event: EventSlider = {
  id: '11111111-1111-4111-8111-111111111111',
  title: 'Live Buddy Day',
  description: 'Meet the community.',
  imageUrl: 'https://storage.example.test/signed-cover',
  imageAlt: 'Students at Buddy Day',
  eventStartAt: '2026-10-10T08:00:00Z',
  eventEndAt: '2026-10-10T10:00:00Z',
  location: 'VGU Campus',
  cta: {
    label: 'View event',
    href: '/events/11111111-1111-4111-8111-111111111111',
  },
  sortOrder: 0,
}

function canonicalEvent(index: number): EventSlider {
  const suffix = String(index).padStart(12, '0')
  const id = `00000000-0000-4000-8000-${suffix}`
  return {
    ...event,
    id,
    title: `Canonical Event ${index}`,
    cta: { label: 'View event', href: `/events/${id}` },
    sortOrder: index - 1,
  }
}

function renderLive(repository: EventSliderRepository) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false, gcTime: 0 } } })
  return render(
    <QueryClientProvider client={client}>
      <LiveEventsSection locale="en" repository={repository} />
    </QueryClientProvider>,
  )
}

describe('FE-014B live Landing Event section', () => {
  beforeEach(async () => {
    await i18n.changeLanguage('en')
  })

  it('reserves poster space while the live request is pending', () => {
    renderLive({ listPublished: () => new Promise(() => undefined) })

    expect(screen.getByRole('status', { name: 'Loading upcoming events' })).toBeVisible()
    expect(screen.getByRole('heading', { name: 'Upcoming Events' })).toBeVisible()
  })

  it('renders a live-shaped Event and its exact detail target', async () => {
    const listPublished = vi.fn().mockResolvedValue([event])
    renderLive({ listPublished })

    const link = await screen.findByRole('link', { name: 'View event: Live Buddy Day' })
    expect(link).toHaveAttribute('href', event.cta?.href)
    expect(screen.getByRole('img', { name: event.imageAlt })).toHaveAttribute('src', event.imageUrl)
    expect(listPublished).toHaveBeenCalledWith('en', expect.any(AbortSignal))
  })

  it('hides the complete section for a successful empty response', async () => {
    const { container } = renderLive({ listPublished: vi.fn().mockResolvedValue([]) })

    await waitFor(() => expect(container).toBeEmptyDOMElement())
    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
  })

  it('shows only the first five Events in canonical API order', async () => {
    renderLive({
      listPublished: vi
        .fn()
        .mockResolvedValue(Array.from({ length: 7 }, (_, index) => canonicalEvent(index + 1))),
    })

    expect(await screen.findByText('Event 1 of 5')).toBeVisible()
    expect(screen.getAllByText('Canonical Event 5').length).toBeGreaterThan(0)
    expect(screen.queryByText('Canonical Event 6')).not.toBeInTheDocument()
    expect(screen.queryByText('Canonical Event 7')).not.toBeInTheDocument()
  })

  it('distinguishes a real failure and retries successfully', async () => {
    const listPublished = vi
      .fn()
      .mockRejectedValueOnce(new Error('private provider detail'))
      .mockResolvedValueOnce([event])
    renderLive({ listPublished })
    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Upcoming events could not be loaded.',
    )
    expect(screen.queryByText(/private provider detail/)).not.toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: 'Try again' }))

    expect(await screen.findByRole('link', { name: 'View event: Live Buddy Day' })).toBeVisible()
    expect(listPublished).toHaveBeenCalledTimes(2)
  })
})
