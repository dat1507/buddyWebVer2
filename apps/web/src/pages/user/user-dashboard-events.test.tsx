import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { act, cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

vi.mock('@/config/launch-scope', () => ({
  adminEventsEnabled: true,
  publicEventsEnabled: true,
}))

import { publicEventsClient, type PublicEvent } from '@/features/events/public-event'
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
const event: PublicEvent = {
  id: EVENT_ID,
  locale: 'en',
  title: 'Buddy Announcement',
  description: 'Registration is open.',
  start_date: null,
  end_date: null,
  timezone: 'Asia/Ho_Chi_Minh',
  location: null,
  category: null,
  organizer: null,
  registration_url: 'https://events.example/register?source=dashboard',
  registration_enabled: true,
  registration_deadline: null,
  status: 'PUBLISHED',
  phase: null,
  cover: null,
}

function page(items: PublicEvent[]) {
  return { items, page: 1, page_size: 100, total: items.length, total_pages: items.length ? 1 : 0 }
}

describe('User Events registration page', () => {
  let client: QueryClient
  const readEvents = vi.spyOn(publicEventsClient, 'readEvents')

  beforeEach(async () => {
    await i18n.changeLanguage('en')
    useAuthStore.getState().resetSession()
    useAuthStore.getState().setAuthenticated(user)
    vi.spyOn(profileClient, 'readOwn').mockResolvedValue(completeOwnProfile)
    vi.spyOn(profileClient, 'readCompletion').mockResolvedValue(completeProfileCompletion)
    readEvents.mockReset().mockResolvedValue(page([event]))
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

    const link = await screen.findByRole('link', { name: 'Register for Buddy Announcement' })
    expect(link).toHaveAttribute('href', event.registration_url)
    expect(link).toHaveAttribute('target', '_blank')
    expect(link).toHaveAttribute('rel', 'noreferrer')
    expect(screen.getByRole('link', { name: 'View Buddy Announcement details' })).toHaveAttribute(
      'href',
      `/events/${EVENT_ID}?from=user-dashboard`,
    )
    expect(readEvents).toHaveBeenCalledWith('en', expect.any(AbortSignal))
  })

  it('hides broken actions when registration is disabled or the URL is missing', async () => {
    readEvents.mockResolvedValueOnce(
      page([
        { ...event, registration_enabled: false },
        { ...event, id: '22222222-2222-4222-8222-222222222222', registration_url: null },
      ]),
    )
    renderEvents()

    expect(await screen.findByRole('heading', { name: 'Events' })).toBeVisible()
    await waitFor(() => expect(readEvents).toHaveBeenCalledTimes(1))
    expect(screen.getByRole('heading', { name: 'No event registrations available' })).toBeVisible()
    expect(screen.queryByRole('link', { name: /Register for/ })).not.toBeInTheDocument()
  })

  it('preserves loading and retry behavior after moving registration to the Events tab', async () => {
    readEvents
      .mockRejectedValueOnce(new Error('network details'))
      .mockResolvedValueOnce(page([event]))
    renderEvents()

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Event registration could not be loaded.',
    )
    expect(screen.queryByText('network details')).not.toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: 'Try again' }))
    expect(
      await screen.findByRole('link', { name: 'Register for Buddy Announcement' }),
    ).toBeVisible()
    expect(readEvents).toHaveBeenCalledTimes(2)
  })

  it('revalidates an updated URL and keeps the German mobile action usable', async () => {
    const updatedUrl = 'https://events.example/register-updated'
    readEvents
      .mockResolvedValueOnce(page([event]))
      .mockResolvedValueOnce(page([{ ...event, registration_url: updatedUrl }]))
      .mockResolvedValueOnce(
        page([
          { ...event, locale: 'de', title: 'Buddy-Ankündigung', registration_url: updatedUrl },
        ]),
      )
    Object.defineProperty(window, 'innerWidth', { configurable: true, value: 390 })
    renderEvents()
    await screen.findByRole('link', { name: 'Register for Buddy Announcement' })

    await act(async () => {
      await client.invalidateQueries({ queryKey: ['events'] })
    })
    await waitFor(() =>
      expect(screen.getByRole('link', { name: 'Register for Buddy Announcement' })).toHaveAttribute(
        'href',
        updatedUrl,
      ),
    )

    await act(async () => {
      await i18n.changeLanguage('de')
    })

    const updated = await screen.findByRole('link', { name: 'Für Buddy-Ankündigung anmelden' })
    expect(updated).toHaveAttribute('href', updatedUrl)
    expect(updated).toHaveClass('w-full')
    expect(readEvents).toHaveBeenCalledWith('de', expect.any(AbortSignal))
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
      screen.queryByRole('link', { name: 'Register for Buddy Announcement' }),
    ).not.toBeInTheDocument()
    expect(readEvents).not.toHaveBeenCalled()
  })
})
