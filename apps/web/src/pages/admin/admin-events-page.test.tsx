import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { act, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { MemoryRouter } from 'react-router'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import App from '@/App'
import { adminEventsClient, type AdminEventList } from '@/features/admin-events/admin-events'
import { clearPrivateQueries } from '@/features/auth/private-cache'
import i18n from '@/i18n'
import { useAuthStore } from '@/stores/auth-store'

const admin = {
  id: 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa',
  email: 'admin@example.com',
  role: 'ADMIN' as const,
  email_verified: true,
  email_verified_at: '2026-09-20T08:30:00Z',
}
const publishedEvent = {
  id: '11111111-1111-4111-8111-111111111111',
  title_en: 'Buddy Day',
  title_de: 'Buddy-Tag',
  description_en: 'Meet the community.',
  description_de: 'Triff die Community.',
  start_date: '2026-10-10T08:00:00Z',
  end_date: '2026-10-10T10:00:00Z',
  timezone: 'Asia/Ho_Chi_Minh',
  location_en: 'VGU Campus',
  location_de: 'VGU-Campus',
  category: 'community',
  organizer: 'VGU Buddy',
  registration_url: null,
  cover_media_id: '22222222-2222-4222-8222-222222222222',
  status: 'PUBLISHED' as const,
  visibility: 'PUBLIC' as const,
  phase: 'UPCOMING' as const,
  registration_enabled: false,
  max_participants: null,
  registration_deadline: null,
  published_at: '2026-10-09T08:00:00Z',
  version: 4,
  created_at: '2026-10-08T08:00:00Z',
  updated_at: '2026-10-09T08:00:00Z',
}
const cancelledEvent = {
  ...publishedEvent,
  id: '33333333-3333-4333-8333-333333333333',
  title_en: 'Cancelled Meetup',
  status: 'CANCELLED' as const,
  phase: 'COMPLETED' as const,
}

function eventPage(total = 2): AdminEventList {
  return {
    items: total ? [publishedEvent, cancelledEvent] : [],
    page: 1,
    page_size: 20,
    total,
    total_pages: total ? 1 : 0,
  }
}

describe('ADMIN-006 guarded Admin Event inventory', () => {
  let client: QueryClient
  const readEvents = vi.spyOn(adminEventsClient, 'readEvents')

  beforeEach(async () => {
    await i18n.changeLanguage('en')
    useAuthStore.getState().resetSession()
    client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
    readEvents.mockReset().mockResolvedValue(eventPage())
  })

  afterEach(() => {
    client.clear()
    useAuthStore.getState().resetSession()
    vi.clearAllMocks()
  })

  const renderApp = (role: 'ADMIN' | 'USER' | null = 'ADMIN') => {
    if (role) useAuthStore.getState().setAuthenticated({ ...admin, role })
    else useAuthStore.getState().clearSession()
    return render(
      <QueryClientProvider client={client}>
        <MemoryRouter initialEntries={['/admin/events']}>
          <App />
        </MemoryRouter>
      </QueryClientProvider>,
    )
  }

  it('renders every editorial state with derived phase and authorized create/edit links', async () => {
    renderApp()
    expect(await screen.findByRole('heading', { name: 'Event management' })).toBeVisible()
    const table = await screen.findByRole('table', { name: 'Event inventory' })
    expect(within(table).getByText('Buddy Day')).toBeVisible()
    expect(within(table).getByText('Published')).toBeVisible()
    expect(within(table).getByText('Upcoming')).toBeVisible()
    expect(within(table).getByText('Cancelled')).toBeVisible()
    expect(within(table).getByText('Completed')).toBeVisible()
    expect(screen.getByRole('link', { name: 'Create Event' })).toHaveAttribute(
      'href',
      '/admin/events/new',
    )
    expect(screen.getByRole('link', { name: 'Edit Buddy Day' })).toHaveAttribute(
      'href',
      `/admin/events/${publishedEvent.id}/edit`,
    )
    expect(screen.queryByText(/object.key|created.by/i)).not.toBeInTheDocument()
  })

  it('debounces search and sends server-owned editorial, audience, phase, and date filters', async () => {
    renderApp()
    await screen.findByText('Buddy Day')
    fireEvent.change(screen.getByRole('searchbox', { name: 'Search Events' }), {
      target: { value: '  Buddy  ' },
    })
    fireEvent.change(screen.getByLabelText('Editorial status'), {
      target: { value: 'PUBLISHED' },
    })
    fireEvent.change(screen.getByLabelText('Audience'), { target: { value: 'PUBLIC' } })
    fireEvent.change(screen.getByLabelText('Schedule phase'), {
      target: { value: 'UPCOMING' },
    })
    fireEvent.change(screen.getByLabelText('From date'), { target: { value: '2026-10-01' } })
    expect(screen.getByText('Choose both dates to apply the date range.')).toBeVisible()
    fireEvent.change(screen.getByLabelText('Through date'), { target: { value: '2026-10-31' } })

    await waitFor(
      () =>
        expect(readEvents).toHaveBeenLastCalledWith(
          expect.objectContaining({
            page: 1,
            search: 'Buddy',
            status: 'PUBLISHED',
            visibility: 'PUBLIC',
            phase: 'UPCOMING',
            from: '2026-10-01T00:00:00.000Z',
            to: '2026-11-01T00:00:00.000Z',
          }),
        ),
      { timeout: 1_500 },
    )
  })

  it('distinguishes loading, true empty, filtered empty, and safe failure states', async () => {
    let resolve!: (value: AdminEventList) => void
    readEvents.mockReset().mockReturnValueOnce(new Promise((done) => (resolve = done)))
    renderApp()
    expect(screen.getByText('Loading data…')).toHaveAttribute('role', 'status')
    await act(async () => resolve(eventPage(0)))
    expect(await screen.findByText('There are no Events to show.')).toBeVisible()

    readEvents.mockRejectedValueOnce(new Error('database credential leaked'))
    fireEvent.change(screen.getByLabelText('Editorial status'), {
      target: { value: 'DRAFT' },
    })
    expect(await screen.findByRole('alert')).toHaveTextContent(
      'The Event list could not be loaded.',
    )
    expect(screen.queryByText(/database credential/i)).not.toBeInTheDocument()

    readEvents.mockResolvedValueOnce(eventPage(0))
    fireEvent.click(screen.getByRole('button', { name: 'Try again' }))
    expect(await screen.findByText('No Events match these filters.')).toBeVisible()
  })

  it.each([['USER', /Connect with/] as const, [null, 'Administration access'] as const])(
    'denies %s before requesting private Event data',
    async (role, publicHeading) => {
      renderApp(role)
      expect(await screen.findByRole('heading', { name: publicHeading })).toBeVisible()
      expect(screen.queryByText('Event management')).not.toBeInTheDocument()
      expect(readEvents).not.toHaveBeenCalled()
    },
  )

  it('uses removable private cache and switches the page to German', async () => {
    renderApp()
    await screen.findByText('Buddy Day')
    expect(
      client.getQueryCache().findAll({ queryKey: ['private', 'admin-events'] }),
    ).not.toHaveLength(0)
    await act(async () => clearPrivateQueries(client))
    expect(client.getQueryCache().findAll({ queryKey: ['private', 'admin-events'] })).toHaveLength(
      0,
    )

    fireEvent.click(screen.getByRole('button', { name: /Switch to German/ }))
    expect(await screen.findByRole('heading', { name: 'Veranstaltungsverwaltung' })).toBeVisible()
    expect(screen.getByRole('table', { name: 'Veranstaltungsübersicht' })).toBeVisible()
    expect(screen.getByText('Veröffentlicht')).toBeVisible()
    expect(screen.getByText('Abgesagt')).toBeVisible()
  })
})
