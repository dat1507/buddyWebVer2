import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import {
  adminUserListPath,
  adminUsersClient,
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

describe('ADMIN-012 admin users API contract', () => {
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
