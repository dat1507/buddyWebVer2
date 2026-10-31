import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { act, cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

vi.mock('@/config/launch-scope', () => ({
  adminEventsEnabled: true,
  publicEventsEnabled: true,
}))

import type { EventSlider } from '@/features/events/event-slider'
import { eventSliderRepository } from '@/features/events/repositories/event-slider-repository-provider'
import { profileClient } from '@/features/profile/profile-client'
import i18n from '@/i18n'
import { UserDashboardPage } from '@/pages/user/user-dashboard-page'
import { UserEventsPage } from '@/pages/user/user-events-page'
import { useAuthStore } from '@/stores/auth-store'
import { completeProfileCompletion } from '@/test/profile-completion'
import { completeOwnProfile } from '@/test/profile'

const EVENT_ID = '11111111-1111-4111-8111-111111111111'
const user = {
  id: 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa',
  email: 'member@example.com',
  role: 'USER' as const,
  email_verified: true,
  email_verified_at: '2026-10-14T08:00:00Z',
}
const event: EventSlider = {
  id: EVENT_ID,
  title: 'Buddy Announcement',
  description: 'Registration is open.',
  imageUrl: 'https://storage.example.test/buddy-announcement',
  imageAlt: 'Buddy Announcement poster',
  eventStartAt: null,
  eventEndAt: null,
  location: null,
  registrationUrl: 'https://events.example/register?source=dashboard',
  registrationEnabled: true,
  cta: { label: 'View event', href: `/events/${EVENT_ID}` },
  sortOrder: 0,
}

describe('User Events synchronized Slider page', () => {
  let client: QueryClient
  const listPublished = vi.spyOn(eventSliderRepository, 'listPublished')

  beforeEach(async () => {
    await i18n.changeLanguage('en')
    useAuthStore.getState().resetSession()
    useAuthStore.getState().setAuthenticated(user)
    vi.spyOn(profileClient, 'readOwn').mockResolvedValue(completeOwnProfile)
    vi.spyOn(profileClient, 'readCompletion').mockResolvedValue(completeProfileCompletion)
    listPublished.mockReset().mockResolvedValue([event])
    client = new QueryClient({ defaultOptions: { queries: { retry: false, gcTime: 0 } } })
  })

  afterEach(() => {
    cleanup()
    client?.clear()
    useAuthStore.getState().resetSession()
    vi.clearAllMocks()
  })

  const renderEvents = () =>
    render(
      <QueryClientProvider client={client}>
        <MemoryRouter>
          <UserEventsPage />
        </MemoryRouter>
      </QueryClientProvider>,
    )

  it('renders the exact persisted HTTPS action for an authorized User', async () => {
    renderEvents()

    const link = await screen.findByRole('link', {
      name: 'Register for this event: Buddy Announcement',
    })
    expect(link).toHaveAttribute('href', event.registrationUrl)
    expect(link).toHaveAttribute('target', '_blank')
    expect(link).toHaveAttribute('rel', 'noreferrer')
    expect(screen.getByRole('link', { name: 'View details: Buddy Announcement' })).toHaveAttribute(
      'href',
      `/events/${EVENT_ID}?from=user-dashboard`,
    )
    expect(screen.getByRole('img', { name: event.imageAlt })).toHaveAttribute('src', event.imageUrl)
    expect(screen.getByText(event.description!)).toBeVisible()
    expect(listPublished).toHaveBeenCalledWith('en', expect.any(AbortSignal))
  })

  it('keeps Slider Events without registration visible with View Details as the primary action', async () => {
    const withoutRegistration = {
      ...event,
      id: '22222222-2222-4222-8222-222222222222',
      title: 'Open Day',
      registrationUrl: null,
      registrationEnabled: false,
      cta: {
        label: 'View event',
        href: '/events/22222222-2222-4222-8222-222222222222',
      },
      sortOrder: 1,
    } satisfies EventSlider
    listPublished.mockResolvedValueOnce([event, withoutRegistration])
    renderEvents()

    expect(await screen.findByRole('heading', { name: 'Open Day' })).toBeVisible()
    expect(
      screen.getByRole('link', { name: 'Register for this event: Buddy Announcement' }),
    ).toBeVisible()
    expect(
      screen.queryByRole('link', { name: 'Register for this event: Open Day' }),
    ).not.toBeInTheDocument()
    const details = screen.getByRole('link', { name: 'View details: Open Day' })
    expect(details).toHaveAttribute(
      'href',
      '/events/22222222-2222-4222-8222-222222222222?from=user-dashboard',
    )
    expect(details).toHaveClass('bg-gradient-to-br')
  })

  it('preserves loading and retry behavior after moving registration to the Events tab', async () => {
    listPublished.mockRejectedValueOnce(new Error('network details')).mockResolvedValueOnce([event])
    renderEvents()

    expect(await screen.findByRole('alert')).toHaveTextContent('Events could not be loaded.')
    expect(screen.queryByText('network details')).not.toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: 'Try again' }))
    expect(
      await screen.findByRole('link', { name: 'Register for this event: Buddy Announcement' }),
    ).toBeVisible()
    expect(listPublished).toHaveBeenCalledTimes(2)
  })

  it('revalidates an updated URL and keeps the German mobile action usable', async () => {
    const updatedUrl = 'https://events.example/register-updated'
    listPublished
      .mockResolvedValueOnce([event])
      .mockResolvedValueOnce([{ ...event, registrationUrl: updatedUrl }])
      .mockResolvedValueOnce([
        { ...event, title: 'Buddy-Ankündigung', registrationUrl: updatedUrl },
      ])
    Object.defineProperty(window, 'innerWidth', { configurable: true, value: 390 })
    renderEvents()
    await screen.findByRole('link', { name: 'Register for this event: Buddy Announcement' })

    await act(async () => {
      await client.invalidateQueries({ queryKey: ['event-sliders'] })
    })
    await waitFor(() =>
      expect(
        screen.getByRole('link', { name: 'Register for this event: Buddy Announcement' }),
      ).toHaveAttribute('href', updatedUrl),
    )

    await act(async () => {
      await i18n.changeLanguage('de')
    })

    const updated = await screen.findByRole('link', {
      name: 'Für diese Veranstaltung anmelden: Buddy-Ankündigung',
    })
    expect(updated).toHaveAttribute('href', updatedUrl)
    expect(updated).toHaveClass('w-full')
    expect(listPublished).toHaveBeenCalledWith('de', expect.any(AbortSignal))
  })

  it('uses the same first-five Slider selection and canonical ordering as the Landing page', async () => {
    const sliderEvents = Array.from({ length: 7 }, (_, index) => {
      const number = index + 1
      const id = `00000000-0000-4000-8000-${String(number).padStart(12, '0')}`
      return {
        ...event,
        id,
        title: `Event ${number}`,
        cta: { label: 'View event', href: `/events/${id}` },
        sortOrder: index,
      }
    })
    listPublished.mockResolvedValueOnce(sliderEvents)
    renderEvents()

    expect(await screen.findByRole('heading', { name: 'Event 5' })).toBeVisible()
    expect(screen.queryByRole('heading', { name: 'Event 6' })).not.toBeInTheDocument()
    expect(screen.queryByRole('heading', { name: 'Event 7' })).not.toBeInTheDocument()
    expect(
      screen.getAllByRole('heading', { level: 3 }).map(({ textContent }) => textContent),
    ).toEqual(['Event 1', 'Event 2', 'Event 3', 'Event 4', 'Event 5'])
  })

  it('does not render registration cards on the dashboard anymore', async () => {
    render(
      <QueryClientProvider client={client}>
        <MemoryRouter>
          <UserDashboardPage />
        </MemoryRouter>
      </QueryClientProvider>,
    )

    expect(await screen.findByRole('heading', { name: 'Dashboard' })).toBeVisible()
    expect(
      screen.queryByRole('link', { name: 'Register for this event: Buddy Announcement' }),
    ).not.toBeInTheDocument()
    expect(listPublished).not.toHaveBeenCalled()
  })
})
