import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import {
  adminEventListPath,
  adminEventsClient,
  type AdminEvent,
  type AdminEventList,
  type AdminEventListRequest,
} from '@/features/admin-events/admin-events'
import { sessionClient } from '@/features/auth/session-client'
import { useAuthStore } from '@/stores/auth-store'

const event: AdminEvent = {
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
  registration_url: 'https://events.example.test/register',
  cover_media_id: '22222222-2222-4222-8222-222222222222',
  status: 'PUBLISHED',
  visibility: 'PUBLIC',
  phase: 'UPCOMING',
  registration_enabled: true,
  max_participants: 100,
  registration_deadline: '2026-10-10T07:00:00Z',
  published_at: '2026-10-09T08:00:00Z',
  version: 4,
  created_at: '2026-10-08T08:00:00Z',
  updated_at: '2026-10-09T08:00:00Z',
}

const page: AdminEventList = {
  items: [event],
  page: 2,
  page_size: 10,
  total: 11,
  total_pages: 2,
}

const request: AdminEventListRequest = {
  page: 2,
  pageSize: 10,
  search: ' Buddy & VGU ',
  status: 'PUBLISHED',
  visibility: 'PUBLIC',
  phase: 'UPCOMING',
  from: '2026-10-01T00:00:00.000Z',
  to: '2026-11-01T00:00:00.000Z',
}

describe('ADMIN-006 Admin Event API contract', () => {
  let fetch: ReturnType<typeof vi.fn<typeof globalThis.fetch>>

  beforeEach(() => {
    useAuthStore.getState().setAuthenticated({
      id: 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa',
      email: 'admin@example.com',
      role: 'ADMIN',
      email_verified: true,
    })
    vi.stubEnv('VITE_API_URL', 'https://api.example.test/api')
    fetch = vi.fn<typeof globalThis.fetch>()
    vi.stubGlobal('fetch', fetch)
  })

  afterEach(() => {
    useAuthStore.getState().resetSession()
    vi.restoreAllMocks()
    vi.unstubAllGlobals()
    vi.unstubAllEnvs()
  })

  it('builds only allowlisted bounded filters and requires a complete date pair', () => {
    expect(adminEventListPath(request)).toBe(
      '/admin/events?page=2&page_size=10&search=Buddy+%26+VGU&status=PUBLISHED&visibility=PUBLIC&phase=UPCOMING&from=2026-10-01T00%3A00%3A00.000Z&to=2026-11-01T00%3A00%3A00.000Z',
    )
    expect(adminEventListPath({ ...request, search: ' ', to: null })).toBe(
      '/admin/events?page=2&page_size=10&status=PUBLISHED&visibility=PUBLIC&phase=UPCOMING',
    )
  })

  it('reads the strict Event page through an authenticated GET', async () => {
    fetch.mockResolvedValueOnce(Response.json(page))

    await expect(adminEventsClient.readEvents(request)).resolves.toEqual(page)
    expect(fetch).toHaveBeenCalledWith(
      `https://api.example.test/api${adminEventListPath(request)}`,
      expect.objectContaining({ method: 'GET', credentials: 'include' }),
    )
  })

  it.each([
    { ...page, items: [{ ...event, created_by: 'private-actor' }] },
    { ...page, items: [{ ...event, object_key: 'private/object.webp' }] },
    { ...page, items: [{ ...event, bucket: 'event-media' }] },
  ])('rejects unexpected actor or storage fields', async (payload) => {
    fetch.mockResolvedValueOnce(Response.json(payload))
    await expect(adminEventsClient.readEvents(request)).rejects.toMatchObject({
      code: 'invalidResponse',
    })
  })

  it('rejects inconsistent totals and duplicate records', async () => {
    fetch
      .mockResolvedValueOnce(Response.json({ ...page, total_pages: 3 }))
      .mockResolvedValueOnce(Response.json({ ...page, items: [event, event] }))

    await expect(adminEventsClient.readEvents(request)).rejects.toMatchObject({
      code: 'invalidResponse',
    })
    await expect(adminEventsClient.readEvents(request)).rejects.toMatchObject({
      code: 'invalidResponse',
    })
  })

  it('creates and updates drafts through JSON and uploads covers through FormData', async () => {
    const authenticatedJson = vi.spyOn(sessionClient, 'authenticatedJson')
    const updated = { ...event, version: 5 }
    const media = {
      id: event.cover_media_id!,
      event_id: event.id,
      usage: 'EVENT_COVER',
      alt_en: 'Poster',
      alt_de: 'Plakat',
      mime_type: 'image/webp',
      byte_size: 1200,
      width: 1200,
      height: 800,
      sort_order: 0,
      processing_status: 'READY',
      created_at: event.created_at,
      updated_at: event.updated_at,
    }
    authenticatedJson
      .mockResolvedValueOnce(event)
      .mockResolvedValueOnce(updated)
      .mockResolvedValueOnce({ event: updated, media, cleanup_pending: false })
    const payload = {
      title_en: 'Buddy Day',
      title_de: 'Buddy-Tag',
      description_en: null,
      description_de: null,
      start_date: event.start_date,
      end_date: event.end_date,
      timezone: event.timezone,
      location_en: null,
      location_de: null,
      category: null,
      organizer: null,
      registration_url: null,
      visibility: 'MEMBERS' as const,
      registration_enabled: false,
      max_participants: null,
      registration_deadline: null,
    }

    await expect(adminEventsClient.createDraft(payload)).resolves.toEqual(event)
    await expect(
      adminEventsClient.updateEvent(event.id, { ...payload, version: event.version }),
    ).resolves.toEqual(updated)
    await expect(
      adminEventsClient.uploadCover({
        eventId: event.id,
        version: updated.version,
        altEn: ' Poster ',
        altDe: ' Plakat ',
        file: new File(['image'], 'cover.webp', { type: 'image/webp' }),
      }),
    ).resolves.toMatchObject({ media })

    expect(authenticatedJson.mock.calls[0]).toEqual([
      '/admin/events',
      { method: 'POST', body: payload },
    ])
    expect(authenticatedJson.mock.calls[1]).toEqual([
      `/admin/events/${event.id}`,
      { method: 'PUT', body: { ...payload, version: event.version } },
    ])
    const uploadOptions = authenticatedJson.mock.calls[2][1]
    expect(uploadOptions).toMatchObject({ method: 'POST' })
    expect(uploadOptions?.formData).toBeInstanceOf(FormData)
    expect(uploadOptions?.formData?.get('version')).toBe('5')
    expect(uploadOptions?.formData?.get('alt_en')).toBe('Poster')
    expect(uploadOptions?.formData?.get('alt_de')).toBe('Plakat')
  })

  it('changes editorial status through the versioned status endpoint', async () => {
    const authenticatedJson = vi.spyOn(sessionClient, 'authenticatedJson')
    const published = { ...event, status: 'PUBLISHED' as const, version: 5 }
    authenticatedJson.mockResolvedValueOnce(published)

    await expect(
      adminEventsClient.setStatus({
        eventId: event.id,
        version: event.version,
        status: 'PUBLISHED',
      }),
    ).resolves.toEqual(published)
    expect(authenticatedJson).toHaveBeenCalledWith(`/admin/events/${event.id}/status`, {
      method: 'PATCH',
      body: { version: event.version, status: 'PUBLISHED' },
    })
  })
})
