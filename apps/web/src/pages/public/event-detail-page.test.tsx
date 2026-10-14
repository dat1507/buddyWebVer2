import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { act, cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes, useNavigate } from 'react-router'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { PublicLayout } from '@/components/layout/public-layout'
import { publicEventsClient, type PublicEvent } from '@/features/events/public-event'
import i18n from '@/i18n'
import { ApiError } from '@/lib/api'
import { EventDetailPage } from '@/pages/public/event-detail-page'
import { useAuthStore } from '@/stores/auth-store'

const FIRST_ID = '11111111-1111-4111-8111-111111111111'
const SECOND_ID = '22222222-2222-4222-8222-222222222222'
const event: PublicEvent = {
  id: FIRST_ID,
  locale: 'en',
  title: 'Buddy Day',
  description: 'Meet <script>unsafe()</script> friends.\nEveryone is welcome.',
  start_date: '2026-10-10T08:00:00Z',
  end_date: '2026-10-10T10:00:00Z',
  timezone: 'Asia/Ho_Chi_Minh',
  location: 'VGU Campus',
  category: 'community',
  organizer: 'VGU Buddy',
  registration_url: null,
  registration_enabled: false,
  registration_deadline: null,
  status: 'PUBLISHED',
  visibility: 'PUBLIC',
  phase: 'UPCOMING',
  cover: {
    url: 'https://storage.example.test/signed-cover',
    alt_text: 'Students at Buddy Day',
    mime_type: 'image/webp',
    width: 1200,
    height: 800,
    expires_in: 300,
  },
}

function EventNavigation() {
  const navigate = useNavigate()
  return (
    <button type="button" onClick={() => void navigate(`/events/${SECOND_ID}`)}>
      Next fixture Event
    </button>
  )
}

function renderEvent(path = `/events/${FIRST_ID}`) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0 } },
  })
  const result = render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={[path]}>
        <Routes>
          <Route element={<PublicLayout />}>
            <Route
              path="events/:eventId"
              element={
                <>
                  <EventNavigation />
                  <EventDetailPage />
                </>
              }
            />
          </Route>
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  )
  return { ...result, client }
}

describe('FE-031 Event detail page', () => {
  const readEvent = vi.spyOn(publicEventsClient, 'readEvent')

  beforeEach(async () => {
    await i18n.changeLanguage('en')
    useAuthStore.getState().clearSession()
    readEvent.mockReset().mockResolvedValue(event)
  })

  afterEach(() => {
    useAuthStore.getState().resetSession()
    vi.clearAllMocks()
  })

  it('waits for session bootstrap before loading a viewer-scoped direct URL', async () => {
    useAuthStore.getState().startLoading()
    renderEvent()

    expect(screen.getByRole('status', { name: 'Loading Event' })).toBeVisible()
    expect(readEvent).not.toHaveBeenCalled()

    act(() => useAuthStore.getState().clearSession())

    expect(await screen.findByRole('heading', { level: 1, name: 'Buddy Day' })).toBeVisible()
    expect(readEvent).toHaveBeenCalledTimes(1)
  })

  it('loads a direct URL and renders authoritative fields, poster, and escaped text', async () => {
    const { container } = renderEvent()

    expect(await screen.findByRole('heading', { level: 1, name: 'Buddy Day' })).toBeVisible()
    expect(screen.getByRole('img', { name: 'Students at Buddy Day' })).toHaveAttribute(
      'src',
      event.cover?.url,
    )
    expect(screen.getByText('VGU Campus')).toBeVisible()
    expect(screen.getAllByText('VGU Buddy')).toHaveLength(3)
    expect(screen.getByText(/Meet <script>unsafe\(\)<\/script> friends/)).toBeVisible()
    expect(screen.getByTestId('event-description')).toHaveTextContent(event.description, {
      normalizeWhitespace: false,
    })
    expect(screen.getByTestId('event-description').textContent).toBe(event.description)
    expect(screen.getByTestId('event-description')).toHaveClass('whitespace-pre-wrap')
    expect(container.querySelector('script')).toBeNull()
    expect(readEvent).toHaveBeenCalledWith(FIRST_ID, 'en', expect.any(AbortSignal))
  })

  it('refetches localized data when the language changes', async () => {
    const german = {
      ...event,
      locale: 'de' as const,
      title: 'Buddy-Tag',
      description: 'Lerne die Community kennen.',
      location: 'VGU-Campus',
    }
    readEvent.mockImplementation(async (_id, locale) => (locale === 'de' ? german : event))
    renderEvent()
    await screen.findByRole('heading', { name: 'Buddy Day' })

    await act(async () => i18n.changeLanguage('de'))

    expect(await screen.findByRole('heading', { name: 'Buddy-Tag' })).toBeVisible()
    expect(screen.getByText('VGU-Campus')).toBeVisible()
    expect(readEvent).toHaveBeenCalledWith(FIRST_ID, 'de', expect.any(AbortSignal))
  })

  it('changes Event content after a route ID change', async () => {
    const second = { ...event, id: SECOND_ID, title: 'Second Event' }
    readEvent.mockImplementation(async (id) => (id === SECOND_ID ? second : event))
    renderEvent()
    await screen.findByRole('heading', { name: 'Buddy Day' })

    fireEvent.click(screen.getByRole('button', { name: 'Next fixture Event' }))

    expect(await screen.findByRole('heading', { name: 'Second Event' })).toBeVisible()
    expect(readEvent).toHaveBeenCalledWith(SECOND_ID, 'en', expect.any(AbortSignal))
  })

  it('reflects an updated canonical Description after the detail query refreshes', async () => {
    const updatedDescription = 'Updated in Admin.\n\nSecond paragraph stays intact.'
    readEvent
      .mockResolvedValueOnce(event)
      .mockResolvedValueOnce({ ...event, description: updatedDescription })
    const { client } = renderEvent()

    expect(await screen.findByTestId('event-description')).toHaveTextContent(event.description, {
      normalizeWhitespace: false,
    })

    await act(async () => {
      await client.invalidateQueries({ queryKey: ['events'] })
    })

    await waitFor(() =>
      expect(screen.getByTestId('event-description').textContent).toBe(updatedDescription),
    )
  })

  it('renders the exact HTTPS registration action only when registration is enabled', async () => {
    const registrationUrl = 'https://events.example/register?source=buddy'
    readEvent.mockResolvedValueOnce({
      ...event,
      registration_enabled: true,
      registration_url: registrationUrl,
    })
    renderEvent()

    const registration = await screen.findByRole('link', { name: 'Register for this Event' })
    expect(registration).toHaveAttribute('href', registrationUrl)
    expect(registration).toHaveAttribute('target', '_blank')
    expect(registration).toHaveAttribute('rel', 'noreferrer')

    cleanup()
    readEvent.mockResolvedValueOnce({ ...event, registration_url: registrationUrl })
    renderEvent()
    await screen.findByRole('heading', { name: 'Buddy Day' })
    expect(screen.queryByRole('link', { name: 'Register for this Event' })).not.toBeInTheDocument()
  })

  it('omits missing announcement facts without formatting invalid dates', async () => {
    readEvent.mockResolvedValueOnce({
      ...event,
      start_date: null,
      end_date: null,
      location: null,
      organizer: null,
      category: null,
      phase: null,
    })
    renderEvent()

    expect(await screen.findByRole('heading', { name: 'Buddy Day' })).toBeVisible()
    expect(screen.queryByText('Starts')).not.toBeInTheDocument()
    expect(screen.queryByText('Ends')).not.toBeInTheDocument()
    expect(screen.queryByText('Location')).not.toBeInTheDocument()
    expect(screen.queryByText('Invalid Date')).not.toBeInTheDocument()
    expect(screen.queryByText('Upcoming')).not.toBeInTheDocument()
  })

  it('uses the same safe not-found state for invalid and API-hidden IDs', async () => {
    const invalid = renderEvent('/events/not-a-uuid')
    expect(await screen.findByRole('heading', { name: 'Event not found' })).toBeVisible()
    expect(readEvent).not.toHaveBeenCalled()
    invalid.unmount()

    readEvent.mockRejectedValueOnce(new ApiError(404, 'notFound'))
    renderEvent()
    expect(await screen.findByRole('heading', { name: 'Event not found' })).toBeVisible()
  })

  it('retries a sanitized API failure and renders the recovered Event', async () => {
    readEvent.mockRejectedValueOnce(new Error('provider secret')).mockResolvedValueOnce(event)
    renderEvent()
    expect(await screen.findByRole('heading', { name: 'Event unavailable' })).toBeVisible()

    fireEvent.click(screen.getByRole('button', { name: 'Try again' }))

    expect(await screen.findByRole('heading', { name: 'Buddy Day' })).toBeVisible()
    await waitFor(() => expect(readEvent).toHaveBeenCalledTimes(2))
    expect(screen.queryByText(/provider secret/)).not.toBeInTheDocument()
  })
})
