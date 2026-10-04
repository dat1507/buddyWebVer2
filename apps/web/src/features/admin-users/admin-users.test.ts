import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import {
  adminUserDetailPath,
  adminUserListPath,
  adminUsersClient,
  type AdminUserDetail,
  type AdminUserList,
} from '@/features/admin-users/admin-users'
import { useAuthStore } from '@/stores/auth-store'

const user = {
  id: '11111111-1111-4111-8111-111111111111',
  email: 'ada@example.com',
  role: 'USER' as const,
  is_active: true,
  email_verified: true,
  created_at: '2026-09-20T08:30:00Z',
  profile: {
    id: '22222222-2222-4222-8222-222222222222',
    full_name: 'Ada Student',
    display_name: 'Ada',
    student_type: 'INTERNATIONAL' as const,
  },
}

const page: AdminUserList = {
  items: [user],
  page: 2,
  page_size: 10,
  total: 11,
  total_pages: 2,
}

const detail: AdminUserDetail = {
  ...user,
  profile: {
    ...user.profile,
    nationality: 'British',
    major: 'Computer Science',
    study_year: 2,
    bio: 'Exchange student',
    home_university: 'Example University',
    arrival_date: '2026-09-01',
    departure_date: '2027-02-28',
    matching_opt_in: true,
    onboarding_completed_at: '2026-09-21T10:00:00Z',
    avatar: {
      id: '33333333-3333-4333-8333-333333333333',
      mime_type: 'image/webp',
      byte_size: 12_345,
      width: 400,
      height: 400,
      processing_status: 'READY',
      created_at: '2026-09-21T10:00:00Z',
    },
  },
}

describe('ADMIN-012/013 admin users API contracts', () => {
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
    vi.unstubAllGlobals()
    vi.unstubAllEnvs()
  })

  it('builds only bounded list parameters and omits blank search', () => {
    expect(adminUserListPath({ page: 2, pageSize: 10, search: ' Ada & Linh ' })).toBe(
      '/admin/users?page=2&page_size=10&search=Ada+%26+Linh',
    )
    expect(adminUserListPath({ page: 1, pageSize: 20, search: '   ' })).toBe(
      '/admin/users?page=1&page_size=20',
    )
  })

  it('reads the strict allowlisted summary through a GET-only session request', async () => {
    fetch.mockResolvedValueOnce(Response.json(page))

    await expect(
      adminUsersClient.readUsers({ page: 2, pageSize: 10, search: 'Ada' }),
    ).resolves.toEqual(page)
    expect(fetch).toHaveBeenCalledWith(
      'https://api.example.test/api/admin/users?page=2&page_size=10&search=Ada',
      expect.objectContaining({ method: 'GET', credentials: 'include' }),
    )
  })

  it('reads the strict coordinator-safe user detail through the BE-013 route', async () => {
    fetch.mockResolvedValueOnce(Response.json(detail))

    await expect(adminUsersClient.readUserDetail({ userId: user.id })).resolves.toEqual(detail)
    expect(adminUserDetailPath(user.id)).toBe(`/admin/users/${user.id}`)
    expect(fetch).toHaveBeenCalledWith(
      `https://api.example.test/api/admin/users/${user.id}`,
      expect.objectContaining({ method: 'GET', credentials: 'include' }),
    )
  })

  it.each([
    { ...detail, password_hash: 'private' },
    { ...detail, last_login: '2026-09-20T08:30:00Z' },
    { ...detail, profile: { ...detail.profile, object_key: 'private/avatar' } },
    {
      ...detail,
      profile: detail.profile
        ? { ...detail.profile, avatar: { ...detail.profile.avatar, storage_key: 'private/avatar' } }
        : null,
    },
  ])('rejects unexpected private fields from user detail', async (payload) => {
    fetch.mockResolvedValueOnce(Response.json(payload))
    await expect(adminUsersClient.readUserDetail({ userId: user.id })).rejects.toMatchObject({
      code: 'invalidResponse',
    })
  })

  it('rejects a detail response whose account id differs from the requested id', async () => {
    fetch.mockResolvedValueOnce(
      Response.json({ ...detail, id: '44444444-4444-4444-8444-444444444444' }),
    )
    await expect(adminUsersClient.readUserDetail({ userId: user.id })).rejects.toMatchObject({
      code: 'invalidResponse',
    })
  })

  it.each([
    { ...page, items: [{ ...user, password_hash: 'private' }] },
    { ...page, items: [{ ...user, last_login: '2026-09-20T08:30:00Z' }] },
    { ...page, items: [{ ...user, profile: { ...user.profile, object_key: 'private/avatar' } }] },
  ])('rejects unexpected credential, activity, or storage fields', async (payload) => {
    fetch.mockResolvedValueOnce(Response.json(payload))
    await expect(
      adminUsersClient.readUsers({ page: 2, pageSize: 10, search: '' }),
    ).rejects.toMatchObject({ code: 'invalidResponse' })
  })

  it('rejects inconsistent totals and duplicate records but accepts an out-of-range empty page', async () => {
    fetch
      .mockResolvedValueOnce(Response.json({ ...page, total_pages: 3 }))
      .mockResolvedValueOnce(Response.json({ ...page, items: [user, user] }))
      .mockResolvedValueOnce(
        Response.json({ items: [], page: 3, page_size: 10, total: 5, total_pages: 1 }),
      )

    await expect(
      adminUsersClient.readUsers({ page: 2, pageSize: 10, search: '' }),
    ).rejects.toMatchObject({ code: 'invalidResponse' })
    await expect(
      adminUsersClient.readUsers({ page: 2, pageSize: 10, search: '' }),
    ).rejects.toMatchObject({ code: 'invalidResponse' })
    await expect(
      adminUsersClient.readUsers({ page: 3, pageSize: 10, search: '' }),
    ).resolves.toMatchObject({ page: 3, total_pages: 1, items: [] })
  })
})
