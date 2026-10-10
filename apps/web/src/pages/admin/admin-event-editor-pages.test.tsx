import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { act, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes, useLocation } from 'react-router'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { AdminLayout } from '@/components/layout/admin-layout'
import { adminEventsClient, type AdminEvent } from '@/features/admin-events/admin-events'
import i18n from '@/i18n'
import { ApiError } from '@/lib/api'
import { AdminEventCreatePage } from '@/pages/admin/admin-event-create-page'
import { AdminEventEditPage } from '@/pages/admin/admin-event-edit-page'
import { useAuthStore } from '@/stores/auth-store'

const EVENT_ID = '11111111-1111-4111-8111-111111111111'
const MEDIA_ID = '22222222-2222-4222-8222-222222222222'
const admin = {
  id: 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa',
  email: 'admin@example.com',
  role: 'ADMIN' as const,
  email_verified: true,
}
const event: AdminEvent = {
  id: EVENT_ID,
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
  cover_media_id: null,
  status: 'DRAFT',
  visibility: 'MEMBERS',
  phase: 'UPCOMING',
  registration_enabled: false,
  max_participants: null,
  registration_deadline: null,
  published_at: null,
  version: 1,
  created_at: '2026-10-09T08:00:00Z',
  updated_at: '2026-10-09T08:00:00Z',
}

function LocationProbe() {
  const location = useLocation()
  return <output data-testid="location">{location.pathname}</output>
}

function deferred<T>() {
  let resolve!: (value: T) => void
  const promise = new Promise<T>((done) => {
    resolve = done
  })
  return { promise, resolve }
}

describe('ADMIN-007/008 Event create and edit pages', () => {
  let client: QueryClient
  const createDraft = vi.spyOn(adminEventsClient, 'createDraft')
  const updateEvent = vi.spyOn(adminEventsClient, 'updateEvent')
  const uploadCover = vi.spyOn(adminEventsClient, 'uploadCover')
  const readEvent = vi.spyOn(adminEventsClient, 'readEvent')
  const readCoverUrl = vi.spyOn(adminEventsClient, 'readCoverUrl')
  const setStatus = vi.spyOn(adminEventsClient, 'setStatus')

  beforeEach(async () => {
    await i18n.changeLanguage('en')
    useAuthStore.getState().resetSession()
    useAuthStore.getState().setAuthenticated(admin)
    client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
    createDraft.mockReset()
    updateEvent.mockReset()
    uploadCover.mockReset()
    readEvent.mockReset().mockResolvedValue(event)
    readCoverUrl.mockReset()
    setStatus.mockReset()
  })

  afterEach(() => {
    client.clear()
    useAuthStore.getState().resetSession()
    vi.clearAllMocks()
  })

  const renderApp = (path: string) =>
    render(
      <QueryClientProvider client={client}>
        <MemoryRouter initialEntries={[path]}>
          <LocationProbe />
          <Routes>
            <Route path="/admin" element={<AdminLayout />}>
              <Route path="events/new" element={<AdminEventCreatePage />} />
              <Route path="events/:eventId/edit" element={<AdminEventEditPage />} />
            </Route>
          </Routes>
        </MemoryRouter>
      </QueryClientProvider>,
    )

  it('creates the draft once, retains a failed cover step, and retries without a duplicate draft', async () => {
    const coverFile = new File(['image'], 'poster.webp', { type: 'image/webp' })
    const updated = { ...event, version: 2 }
    const covered = { ...event, version: 3, cover_media_id: MEDIA_ID }
    createDraft.mockResolvedValue(event)
    uploadCover.mockRejectedValueOnce(new ApiError(503, 'server')).mockResolvedValueOnce({
      event: covered,
      media: {
        id: MEDIA_ID,
        event_id: EVENT_ID,
        usage: 'EVENT_COVER',
        alt_en: 'Poster',
        alt_de: 'Plakat',
        mime_type: 'image/webp',
        byte_size: 5,
        width: 10,
        height: 10,
        sort_order: 0,
        processing_status: 'READY',
        created_at: event.created_at,
        updated_at: event.updated_at,
      },
      cleanup_pending: false,
    })
    updateEvent.mockResolvedValue(updated)
    renderApp('/admin/events/new')

    fireEvent.change(screen.getByLabelText('Choose cover image'), {
      target: { files: [coverFile] },
    })
    fireEvent.change(screen.getByLabelText('English alternative text'), {
      target: { value: 'Poster' },
    })
    fireEvent.change(screen.getByLabelText('German alternative text'), {
      target: { value: 'Plakat' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Create draft' }))

    expect(await screen.findByText(/draft was saved, but the cover upload failed/i)).toBeVisible()
    expect(createDraft).toHaveBeenCalledTimes(1)
    expect(uploadCover).toHaveBeenCalledTimes(1)
    expect((screen.getByLabelText('Choose cover image') as HTMLInputElement).files?.[0]).toBe(
      coverFile,
    )

    fireEvent.click(screen.getByRole('button', { name: 'Save draft and retry cover' }))
    await waitFor(() =>
      expect(screen.getByTestId('location')).toHaveTextContent(`/admin/events/${EVENT_ID}/edit`),
    )
    expect(createDraft).toHaveBeenCalledTimes(1)
    expect(updateEvent).toHaveBeenCalledWith(EVENT_ID, expect.objectContaining({ version: 1 }))
    expect(uploadCover).toHaveBeenCalledTimes(2)
  })

  it('locks synchronous repeated submission so one click sequence cannot create duplicates', async () => {
    const pending = deferred<AdminEvent>()
    createDraft.mockReturnValue(pending.promise)
    renderApp('/admin/events/new')
    const submit = screen.getByRole('button', { name: 'Create draft' })

    fireEvent.click(submit)
    fireEvent.click(submit)
    await waitFor(() => expect(createDraft).toHaveBeenCalledTimes(1))
    await act(async () => pending.resolve(event))
    await waitFor(() =>
      expect(screen.getByTestId('location')).toHaveTextContent(`/admin/events/${EVENT_ID}/edit`),
    )
  })

  it('rejects an invalid cover before creating any draft and presents German labels', async () => {
    renderApp('/admin/events/new')
    fireEvent.change(screen.getByLabelText('Choose cover image'), {
      target: { files: [new File(['svg'], 'poster.svg', { type: 'image/svg+xml' })] },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Create draft' }))
    expect(await screen.findByText('Choose a JPEG, PNG or WebP image.')).toBeVisible()
    expect(createDraft).not.toHaveBeenCalled()

    fireEvent.click(screen.getByRole('button', { name: /Switch to German/ }))
    expect(
      await screen.findByRole('heading', { name: 'Veranstaltungsentwurf erstellen' }),
    ).toBeVisible()
    expect(screen.getByText('Titelbild auswählen')).toBeVisible()
  })

  it('prefills edit data and preserves changed values when an optimistic update conflicts', async () => {
    updateEvent.mockRejectedValueOnce(new ApiError(409, 'conflict'))
    renderApp(`/admin/events/${EVENT_ID}/edit`)
    const title = (await screen.findAllByLabelText('Title'))[0]
    expect(title).toHaveValue('Buddy Day')
    fireEvent.change(title, { target: { value: 'Changed Buddy Day' } })
    fireEvent.click(screen.getByRole('button', { name: 'Save changes' }))

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'The Event changed in another session. Reload and review before saving again.',
    )
    expect(title).toHaveValue('Changed Buddy Day')
    expect(updateEvent).toHaveBeenCalledWith(
      EVENT_ID,
      expect.objectContaining({ version: 1, title_en: 'Changed Buddy Day' }),
    )
  })

  it('shows actionable publication gaps without calling the status API', async () => {
    renderApp(`/admin/events/${EVENT_ID}/edit`)
    await screen.findByRole('heading', { name: 'Edit Event' })

    fireEvent.click(screen.getByRole('button', { name: 'Publish' }))

    const readiness = await screen.findByRole('alert')
    expect(readiness).toHaveTextContent('Ready managed cover')
    expect(setStatus).not.toHaveBeenCalled()
  })

  it('publishes once, waits for the server, and refreshes the authoritative status', async () => {
    const eligible = { ...event, visibility: 'PUBLIC' as const, cover_media_id: MEDIA_ID }
    const published = {
      ...eligible,
      status: 'PUBLISHED' as const,
      version: 2,
      published_at: '2026-10-09T09:00:00Z',
    }
    const pending = deferred<AdminEvent>()
    readEvent.mockReset().mockResolvedValueOnce(eligible).mockResolvedValue(published)
    readCoverUrl.mockResolvedValue({
      id: MEDIA_ID,
      event_id: EVENT_ID,
      url: 'https://storage.example.test/signed-cover',
      expires_in: 300,
    })
    setStatus.mockReturnValue(pending.promise)
    renderApp(`/admin/events/${EVENT_ID}/edit`)
    const publish = await screen.findByRole('button', { name: 'Publish' })

    fireEvent.click(publish)
    fireEvent.click(publish)
    await waitFor(() => expect(setStatus).toHaveBeenCalledTimes(1))
    expect(screen.queryByText('Event status changed to Published.')).not.toBeInTheDocument()

    await act(async () => pending.resolve(published))
    expect(await screen.findByText('Event status changed to Published.')).toBeVisible()
    await waitFor(() => expect(screen.getByText(/Current status: Published/)).toBeVisible())
    expect(setStatus).toHaveBeenCalledWith({
      eventId: EVENT_ID,
      version: 1,
      status: 'PUBLISHED',
    })
  })

  it('requires confirmation before unpublishing or cancelling', async () => {
    const published = {
      ...event,
      cover_media_id: MEDIA_ID,
      status: 'PUBLISHED' as const,
      version: 4,
      published_at: '2026-10-09T09:00:00Z',
    }
    const draft = { ...published, status: 'DRAFT' as const, version: 5 }
    readEvent.mockReset().mockResolvedValueOnce(published).mockResolvedValue(draft)
    readCoverUrl.mockResolvedValue({
      id: MEDIA_ID,
      event_id: EVENT_ID,
      url: 'https://storage.example.test/signed-cover',
      expires_in: 300,
    })
    setStatus.mockResolvedValue(draft)
    renderApp(`/admin/events/${EVENT_ID}/edit`)

    fireEvent.click(await screen.findByRole('button', { name: 'Move to draft' }))
    expect(await screen.findByRole('alertdialog')).toHaveTextContent(
      'The Event and its linked public promotion will be hidden.',
    )
    expect(setStatus).not.toHaveBeenCalled()
    fireEvent.click(screen.getByRole('alertdialog').querySelector('button:last-child')!)
    await waitFor(() =>
      expect(setStatus).toHaveBeenCalledWith({
        eventId: EVENT_ID,
        version: 4,
        status: 'DRAFT',
      }),
    )

    await waitFor(() => expect(screen.getByText(/Current status: Draft/)).toBeVisible())
    fireEvent.click(screen.getByRole('button', { name: 'Cancel Event' }))
    expect(await screen.findByRole('alertdialog')).toHaveTextContent(
      'The cancellation remains visible to its intended audience',
    )
  })
})
