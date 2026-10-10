import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { cleanup, render, screen, waitFor, within } from '@testing-library/react'
import { MemoryRouter } from 'react-router'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import App from '@/App'
import { AdminOverviewPage } from '@/pages/admin/admin-overview-page'
import { LandingPage } from '@/pages/public/landing-page'
import { adminEventsEnabled, publicEventsEnabled } from '@/config/launch-scope'
import { adminEventsClient } from '@/features/admin-events/admin-events'
import { publicEventsClient } from '@/features/events/public-event'
import { eventSliderRepository } from '@/features/events/repositories/event-slider-repository-provider'
import i18n from '@/i18n'
import { adminRoutes } from '@/routes/admin-routes'
import { userNavigationItems } from '@/routes/user-navigation'
import { userRoutes } from '@/routes/user-routes'
import { useAuthStore } from '@/stores/auth-store'

const EVENT_ID = '11111111-1111-4111-8111-111111111111'
const admin = {
  id: 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa',
  email: 'admin@example.com',
  role: 'ADMIN' as const,
  email_verified: true,
}
const user = {
  ...admin,
  role: 'USER' as const,
  email: 'student@example.com',
  email_verified_at: '2026-10-10T00:00:00Z',
}
const publicEvent = {
  id: EVENT_ID,
  locale: 'en' as const,
  title: 'Live matrix Event',
  description: 'Public Event route fixture.',
  start_date: '2026-11-01T09:00:00+07:00',
  end_date: '2026-11-01T11:00:00+07:00',
  timezone: 'Asia/Ho_Chi_Minh',
  location: 'VGU campus',
  category: null,
  organizer: null,
  registration_url: null,
  registration_enabled: false,
  registration_deadline: null,
  status: 'PUBLISHED' as const,
  visibility: 'PUBLIC' as const,
  phase: 'UPCOMING' as const,
  cover: null,
}

function testClient() {
  return new QueryClient({ defaultOptions: { queries: { retry: false, gcTime: 0 } } })
}

function renderWithRouter(element: React.ReactNode, path = '/') {
  const client = testClient()
  const view = render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={[path]}>{element}</MemoryRouter>
    </QueryClientProvider>,
  )
  return { ...view, client }
}

describe('independent Event feature-flag integration', () => {
  beforeEach(async () => {
    await i18n.changeLanguage('en')
    useAuthStore.getState().resetSession()
  })

  afterEach(() => {
    cleanup()
    useAuthStore.getState().resetSession()
    vi.restoreAllMocks()
  })

  it('matches the exact environment values and scopes route/navigation metadata independently', () => {
    expect(adminEventsEnabled).toBe(import.meta.env.VITE_ADMIN_EVENTS_ENABLED === 'true')
    expect(publicEventsEnabled).toBe(import.meta.env.VITE_PUBLIC_EVENTS_ENABLED === 'true')
    expect(adminRoutes.some(({ path }) => path === 'events')).toBe(adminEventsEnabled)
    expect(userRoutes.some(({ path }) => path === 'events')).toBe(publicEventsEnabled)
    expect(userNavigationItems.some(({ id }) => id === 'events')).toBe(publicEventsEnabled)

    render(<AdminOverviewPage />)
    const overview = screen.getByRole('region', { name: 'Admin overview' })
    expect(within(overview).queryByText('Published Events') !== null).toBe(adminEventsEnabled)
    expect(within(overview).queryByText('Upcoming Events') !== null).toBe(adminEventsEnabled)
  })

  it('uses the API-backed Landing section only when the public flag is on', async () => {
    const listPublished = vi.spyOn(eventSliderRepository, 'listPublished').mockResolvedValue([])
    const { client } = renderWithRouter(<LandingPage />)

    if (publicEventsEnabled) {
      await waitFor(() => expect(listPublished).toHaveBeenCalledWith('en', expect.any(AbortSignal)))
      expect(
        await screen.findByText('There are no upcoming events to show right now.'),
      ).toBeVisible()
      expect(screen.queryByText('Recruitment')).not.toBeInTheDocument()
    } else {
      expect(await screen.findAllByText('Recruitment')).not.toHaveLength(0)
      expect(listPublished).not.toHaveBeenCalled()
    }
    client.clear()
  })

  it.each([
    ['/admin/events', 'Event management'],
    ['/admin/events/new', 'Create Event draft'],
    [`/admin/events/${EVENT_ID}/edit`, null],
  ] as const)(
    'handles the direct Admin Event path %s consistently behind the Admin role guard',
    (path, heading) => {
      vi.spyOn(adminEventsClient, 'readEvents').mockReturnValue(new Promise(() => undefined))
      vi.spyOn(adminEventsClient, 'readEvent').mockReturnValue(new Promise(() => undefined))
      useAuthStore.getState().setAuthenticated(admin)
      const { client } = renderWithRouter(<App />, path)
      const nav = screen.getByRole('navigation', { name: 'Administrator navigation' })

      if (adminEventsEnabled) {
        if (heading) {
          expect(screen.getByRole('heading', { level: 1, name: heading })).toBeVisible()
        } else {
          expect(screen.getByRole('status')).toHaveTextContent('Loading Event')
        }
        expect(within(nav).getByRole('link', { name: 'Events' })).toBeVisible()
      } else {
        expect(screen.getByRole('heading', { level: 1, name: 'Page not found' })).toBeVisible()
        expect(within(nav).queryByRole('link', { name: 'Events' })).not.toBeInTheDocument()
      }
      client.clear()
    },
  )

  it('handles User Event routes and navigation only with the public flag', () => {
    useAuthStore.getState().setAuthenticated(user)
    const { client } = renderWithRouter(<App />, '/user/events')
    const nav = screen.getByRole('navigation', { name: 'Student navigation' })

    if (publicEventsEnabled) {
      expect(screen.getByRole('heading', { name: 'Events' })).toBeVisible()
      expect(within(nav).getByText('Events')).toBeVisible()
    } else {
      expect(screen.getByRole('heading', { level: 1, name: 'Page not found' })).toBeVisible()
      expect(within(nav).queryByText('Events')).not.toBeInTheDocument()
    }
    client.clear()
  })

  it('registers the public Event detail route only with the public flag', async () => {
    const readEvent = vi.spyOn(publicEventsClient, 'readEvent').mockResolvedValue(publicEvent)
    useAuthStore.getState().clearSession()
    const { client } = renderWithRouter(<App />, `/events/${EVENT_ID}`)

    if (publicEventsEnabled) {
      expect(
        await screen.findByRole('heading', { level: 1, name: publicEvent.title }),
      ).toBeVisible()
      expect(readEvent).toHaveBeenCalledWith(EVENT_ID, 'en', expect.any(AbortSignal))
    } else {
      expect(screen.getByRole('heading', { level: 1, name: 'Page not found' })).toBeVisible()
      expect(readEvent).not.toHaveBeenCalled()
    }
    client.clear()
  })

  it('never uses the frontend flag as Admin authorization', async () => {
    useAuthStore.getState().setAuthenticated(user)
    const { client } = renderWithRouter(<App />, '/admin/events/new')

    expect(await screen.findByRole('heading', { name: /Connect with/ })).toBeVisible()
    expect(document.querySelector('[data-layout="admin"]')).toBeNull()
    client.clear()
  })
})
