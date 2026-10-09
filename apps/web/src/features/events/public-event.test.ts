import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { publicEventSchema, publicEventsClient } from '@/features/events/public-event'

const EVENT_ID = '11111111-1111-4111-8111-111111111111'
const payload = {
  id: EVENT_ID,
  locale: 'en',
  title: 'Buddy Day',
  description: 'Meet the community.',
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

describe('FE-031 public Event API contract', () => {
  beforeEach(() => {
    vi.stubEnv('VITE_API_URL', 'https://api.example.test/api')
  })

  afterEach(() => {
    vi.restoreAllMocks()
    vi.unstubAllEnvs()
  })

  it('reads a localized Event with credentials through the exact detail route', async () => {
    const fetch = vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(Response.json(payload))

    await expect(publicEventsClient.readEvent(EVENT_ID, 'en')).resolves.toEqual(payload)
    expect(fetch).toHaveBeenCalledWith(
      `https://api.example.test/api/events/${EVENT_ID}?locale=en`,
      expect.objectContaining({ method: 'GET', credentials: 'include' }),
    )
  })

  it('rejects leaked internal fields, an identity mismatch, and non-HTTPS media', async () => {
    vi.spyOn(globalThis, 'fetch')
      .mockResolvedValueOnce(Response.json({ ...payload, cover_media_id: 'private-id' }))
      .mockResolvedValueOnce(
        Response.json({ ...payload, id: '22222222-2222-4222-8222-222222222222' }),
      )
      .mockResolvedValueOnce(
        Response.json({ ...payload, cover: { ...payload.cover, url: 'http://unsafe.test/cover' } }),
      )

    await expect(publicEventsClient.readEvent(EVENT_ID, 'en')).rejects.toMatchObject({
      code: 'invalidResponse',
    })
    await expect(publicEventsClient.readEvent(EVENT_ID, 'en')).rejects.toMatchObject({
      code: 'invalidResponse',
    })
    await expect(publicEventsClient.readEvent(EVENT_ID, 'en')).rejects.toMatchObject({
      code: 'invalidResponse',
    })
  })

  it('requires the end to follow the start', () => {
    expect(publicEventSchema.safeParse({ ...payload, end_date: payload.start_date }).success).toBe(
      false,
    )
  })
})
