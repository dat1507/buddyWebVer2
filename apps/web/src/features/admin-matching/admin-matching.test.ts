import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import {
  adminMatchingClient,
  participantListPath,
  type AdminMatchingParticipantRequest,
} from '@/features/admin-matching/admin-matching'
import { useAuthStore } from '@/stores/auth-store'

const profileId = '11111111-1111-4111-8111-111111111111'
const request: AdminMatchingParticipantRequest = {
  page: 2,
  pageSize: 10,
  studentType: 'INTERNATIONAL',
  verified: false,
  zeroBuddiesOnly: true,
}
const stats = {
  participant_count: 12,
  verified_participant_count: 9,
  active_match_count: 4,
  zero_buddy_participant_count: 3,
  invitations: { pending: 2, accepted: 4, declined: 1, cancelled: 2, expired: 5 },
}
const summary = {
  profile_id: profileId,
  display_name: 'Linh',
  student_type: 'VIETNAMESE' as const,
  is_active: true,
  email_verified: true,
  matching_opt_in: true,
  buddy_count: 1,
}
const profile = {
  id: profileId,
  display_name: 'Linh',
  student_type: 'VIETNAMESE' as const,
  major: 'Computer Science',
  avatar: null,
  interests: [],
  languages: [],
  activities: [],
  availability: null,
}

describe('ADMIN-V2-002 matching monitoring client contracts', () => {
  let fetch: ReturnType<typeof vi.fn<typeof globalThis.fetch>>

  beforeEach(() => {
    useAuthStore.getState().setAuthenticated({
      id: 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa',
      email: 'admin@example.com',
      role: 'ADMIN',
      email_verified: false,
    })
    vi.stubEnv('VITE_API_URL', 'https://api.example.test/api')
    fetch = vi.fn<typeof globalThis.fetch>()
    vi.stubGlobal('fetch', fetch)
  })

  afterEach(() => {
    useAuthStore.getState().resetSession()
    vi.unstubAllGlobals()
    vi.unstubAllEnvs()
  })

  it('builds only the supported deterministic server filters', () => {
    expect(participantListPath(request)).toBe(
      '/admin/matching/participants?page=2&page_size=10&student_type=INTERNATIONAL&verified=false&zero_buddies_only=true',
    )
    expect(
      participantListPath({
        ...request,
        page: 1,
        pageSize: 20,
        studentType: null,
        verified: null,
        zeroBuddiesOnly: false,
      }),
    ).toBe('/admin/matching/participants?page=1&page_size=20')
  })

  it('reads stats, participant pages, and localized safe detail through GET-only session calls', async () => {
    fetch
      .mockResolvedValueOnce(Response.json(stats))
      .mockResolvedValueOnce(
        Response.json({ items: [summary], page: 2, page_size: 10, total: 11, total_pages: 2 }),
      )
      .mockResolvedValueOnce(
        Response.json({
          profile,
          is_active: true,
          email_verified: true,
          matching_opt_in: true,
          buddy_count: 1,
        }),
      )

    await expect(adminMatchingClient.readStats()).resolves.toEqual(stats)
    await expect(adminMatchingClient.readParticipants(request)).resolves.toMatchObject({
      items: [summary],
      total: 11,
    })
    await expect(
      adminMatchingClient.readParticipantDetail({ profileId, locale: 'de' }),
    ).resolves.toMatchObject({ profile, buddy_count: 1 })

    expect(fetch.mock.calls.map(([url, options]) => [url, options?.method])).toEqual([
      ['https://api.example.test/api/admin/matching/stats', 'GET'],
      [
        'https://api.example.test/api/admin/matching/participants?page=2&page_size=10&student_type=INTERNATIONAL&verified=false&zero_buddies_only=true',
        'GET',
      ],
      [`https://api.example.test/api/admin/matching/participants/${profileId}?locale=de`, 'GET'],
    ])
  })

  it.each([
    { ...stats, internal_user_count: 99 },
    {
      items: [{ ...summary, email: 'private@example.com' }],
      page: 1,
      page_size: 20,
      total: 1,
      total_pages: 1,
    },
    {
      profile: { ...profile, user_id: 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa' },
      is_active: true,
      email_verified: true,
      matching_opt_in: true,
      buddy_count: 1,
    },
  ])('rejects unexpected private or internal response fields', async (payload) => {
    fetch.mockResolvedValueOnce(Response.json(payload))
    const read =
      'internal_user_count' in payload
        ? adminMatchingClient.readStats()
        : 'items' in payload
          ? adminMatchingClient.readParticipants({ ...request, page: 1, pageSize: 20 })
          : adminMatchingClient.readParticipantDetail({ profileId, locale: 'en' })
    await expect(read).rejects.toMatchObject({ code: 'invalidResponse' })
  })

  it('rejects inconsistent pagination without exposing response contents', async () => {
    fetch.mockResolvedValueOnce(
      Response.json({
        items: [summary, summary],
        page: 1,
        page_size: 20,
        total: 2,
        total_pages: 1,
      }),
    )
    await expect(
      adminMatchingClient.readParticipants({ ...request, page: 1, pageSize: 20 }),
    ).rejects.toMatchObject({
      name: 'ApiError',
      message: 'API request failed (invalidResponse).',
    })
  })
})
