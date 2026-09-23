import { StrictMode } from 'react'
import { QueryClientProvider } from '@tanstack/react-query'
import { act, cleanup, render, screen, waitFor, within } from '@testing-library/react'
import { MemoryRouter, useLocation } from 'react-router'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import App from '@/App'
import { sessionClient } from '@/features/auth/session-client'
import { SessionBootstrap } from '@/features/auth/session-controls'
import { profileClient } from '@/features/profile/profile-client'
import i18n from '@/i18n'
import { queryClient } from '@/lib/query-client'
import { useAuthStore } from '@/stores/auth-store'
import { completeProfileCompletion } from '@/test/profile-completion'
import { completeOwnProfile } from '@/test/profile'

const user = {
  id: 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa',
  email: 'student@example.com',
  role: 'USER',
  email_verified: false,
}
const json = (value: unknown, status = 200) => new Response(JSON.stringify(value), { status })
function deferred<T>() {
  let resolve!: (value: T) => void
  const promise = new Promise<T>((done) => {
    resolve = done
  })
  return { promise, resolve }
}
function LocationProbe() {
  const { pathname, search, hash } = useLocation()
  return <div data-testid="location">{pathname + search + hash}</div>
}

describe('AUTH-006 App roles + verified AUTH-021 session client', () => {
  let fetch: ReturnType<typeof vi.fn<typeof globalThis.fetch>>
  beforeEach(async () => {
    await i18n.changeLanguage('en')
    useAuthStore.getState().resetSession()
    queryClient.setQueryData(['profile', 'own'], completeOwnProfile)
    queryClient.setQueryData(['profile', 'completion'], completeProfileCompletion)
    vi.spyOn(profileClient, 'readOwn').mockResolvedValue(completeOwnProfile)
    vi.spyOn(profileClient, 'readCompletion').mockResolvedValue(completeProfileCompletion)
    vi.spyOn(profileClient, 'readInterests').mockImplementation(async (locale) => ({
      locale,
      items: [],
    }))
    vi.spyOn(profileClient, 'readLanguages').mockImplementation(async (locale) => ({
      locale,
      items: [],
    }))
    vi.spyOn(profileClient, 'readPhotoUrl').mockResolvedValue({
      id: completeOwnProfile.avatar!.id,
      url: 'https://media.example.test/avatar',
      expires_in: 300,
      expiresAt: Date.now() + 300_000,
    })

    vi.stubEnv('VITE_API_URL', 'http://localhost:8000/api')
    fetch = vi.fn<typeof globalThis.fetch>()
    vi.stubGlobal('fetch', fetch)
  })
  afterEach(async () => {
    cleanup()
    fetch.mockReset().mockImplementation(async (url) => {
      if (String(url).endsWith('/auth/csrf/session')) return json({}, 401)
      if (String(url).endsWith('/auth/csrf')) return json({ csrf_token: 'cleanup' })
      return new Response(null, { status: 204 })
    })
    await sessionClient.logout().catch(() => undefined)
    queryClient.clear()
    useAuthStore.getState().resetSession()
    vi.unstubAllGlobals()
    vi.unstubAllEnvs()
  })
  const renderApp = (path: string, bootstrap = false) =>
    render(
      <StrictMode>
        <QueryClientProvider client={queryClient}>
          <MemoryRouter initialEntries={[path]}>
            <LocationProbe />
            {bootstrap ? <SessionBootstrap /> : null}
            <App />
          </MemoryRouter>
        </QueryClientProvider>
      </StrictMode>,
    )
  const location = () => screen.getByTestId('location').textContent
  const expectNoPrivateLayout = () => {
    expect(document.querySelector('[data-layout="user"]')).toBeNull()
    expect(document.querySelector('[data-layout="admin"]')).toBeNull()
  }

  it.each([
    '/admin',
    '/admin/dashboard',
    '/admin/users',
    '/admin/matching',
    '/admin/events',
    '/admin/announcements',
    '/admin/knowledge-base',
    '/admin/campus',
    '/admin/analytics',
    '/admin/audit-log',
    '/admin/settings',
    '/user',
    '/user/dashboard',
    '/user/profile',
    '/user/matching',
    '/user/buddy',
    '/user/assistant',
    '/user/campus',
    '/user/events',
    '/user/settings',
  ])('blocks the wrong role on declared route %s including private base indexes', async (path) => {
    const role = path.startsWith('/admin') ? 'USER' : 'ADMIN'
    useAuthStore.getState().setAuthenticated({ ...user, role })
    renderApp(path + '?next=https://example.com#private')
    expect(await screen.findByRole('heading', { name: /Connect with/ })).toBeVisible()
    expect(location()).toBe('/')
    expectNoPrivateLayout()
    expect(useAuthStore.getState()).toMatchObject({ status: 'authenticated', role })
    expect(fetch).not.toHaveBeenCalled()
    expect(screen.queryByRole('link', { name: /admin/i })).not.toBeInTheDocument()
  })

  it.each([
    ['/user/profile/edit?view=details#photo', 'USER', 'Edit profile', 'user'],
    ['/admin/audit-log?view=details#entry', 'ADMIN', 'Audit log', 'admin'],
  ])(
    'allows a matching role at %s with its deep link intact',
    async (path, role, title, layout) => {
      useAuthStore.getState().setAuthenticated({ ...user, role })
      renderApp(path)
      expect(await screen.findByRole('heading', { name: title })).toBeVisible()
      expect(document.querySelector(`[data-layout="${layout}"]`)).not.toBeNull()
      expect(location()).toBe(path)
      expect(fetch).not.toHaveBeenCalled()
    },
  )

  it.each([
    ['/user', 'unknown'],
    ['/user', 'loading'],
    ['/admin', 'unknown'],
    ['/admin', 'loading'],
  ])('keeps %s URL unchanged during %s without running its index redirect', (path, status) => {
    if (status === 'loading') useAuthStore.getState().startLoading()
    renderApp(path)
    expect(screen.getByRole('status')).toHaveTextContent('Checking your session…')
    expectNoPrivateLayout()
    expect(location()).toBe(path)
  })

  it.each([
    ['/admin/audit-log', 'USER', false],
    ['/user/profile', 'ADMIN', false],
    ['/admin/audit-log', 'ADMIN', true],
    ['/user/profile/edit', 'USER', true],
  ] as const)('waits for /me before deciding %s access for %s', async (path, role, allowed) => {
    const me = deferred<Response>()
    fetch.mockResolvedValueOnce(json({ csrf_token: 'recovered' })).mockReturnValueOnce(me.promise)
    renderApp(path + '?view=details#entry', true)
    try {
      await waitFor(() => expect(fetch).toHaveBeenCalledTimes(2))
      expect(within(screen.getByRole('main')).getByRole('status')).toHaveTextContent(
        'Checking your session…',
      )
      expectNoPrivateLayout()
      expect(location()).toBe(path + '?view=details#entry')
    } finally {
      await act(async () => me.resolve(json({ ...user, role })))
    }
    await waitFor(() => expect(useAuthStore.getState().status).toBe('authenticated'))
    if (allowed) {
      expect(
        await screen.findByRole('heading', {
          name: role === 'USER' ? 'Edit profile' : 'Audit log',
        }),
      ).toBeVisible()
      expect(location()).toBe(path + '?view=details#entry')
    } else {
      expect(await screen.findByRole('heading', { name: /Connect with/ })).toBeVisible()
      expectNoPrivateLayout()
      expect(location()).toBe('/')
    }
    expect(fetch).toHaveBeenCalledTimes(2) // StrictMode never duplicates session verification.
  })

  it('uses final /me role after expired access rather than the earlier refresh payload', async () => {
    const me = deferred<Response>()
    fetch
      .mockResolvedValueOnce(json({ csrf_token: 'recovered' }))
      .mockResolvedValueOnce(json({}, 401))
      .mockResolvedValueOnce(json({ user: { ...user, role: 'ADMIN' }, csrf_token: 'rotated' }))
      .mockReturnValueOnce(me.promise)
    renderApp('/admin/users', true)
    try {
      await waitFor(() => expect(fetch).toHaveBeenCalledTimes(4))
      expect(useAuthStore.getState().status).toBe('loading')
      expectNoPrivateLayout()
      expect(location()).toBe('/admin/users')
    } finally {
      await act(async () => me.resolve(json(user)))
    }
    expect(await screen.findByRole('heading', { name: /Connect with/ })).toBeVisible()
    expectNoPrivateLayout()
    expect(useAuthStore.getState().role).toBe('USER')
    expect(fetch).toHaveBeenCalledTimes(4)
  })

  it.each([
    ['/admin/users', 'ADMIN', 'USER', 'User management'],
    ['/user/profile/edit', 'USER', 'ADMIN', 'Edit profile'],
  ])(
    'verified refresh role change removes %s and clears private cache',
    async (path, oldRole, newRole, title) => {
      useAuthStore.getState().setAuthenticated({ ...user, role: oldRole })
      queryClient.setQueryData(['profile', user.id], { sensitive: true })
      queryClient.setQueryData(['private', 'admin-users'], [{ sensitive: true }])
      queryClient.setQueryData(['event-sliders', 'en'], ['public'])
      fetch
        .mockResolvedValueOnce(json({ csrf_token: 'recovered' }))
        .mockResolvedValueOnce(json({ user: { ...user, role: newRole }, csrf_token: 'rotated' }))
      renderApp(path)
      expect(await screen.findByRole('heading', { name: title })).toBeVisible()
      await act(async () => sessionClient.refresh())
      expect(await screen.findByRole('heading', { name: /Connect with/ })).toBeVisible()
      expectNoPrivateLayout()
      expect(location()).toBe('/')
      expect(useAuthStore.getState()).toMatchObject({ status: 'authenticated', role: newRole })
      expect(queryClient.getQueryData(['profile', user.id])).toBeUndefined()
      expect(queryClient.getQueryData(['private', 'admin-users'])).toBeUndefined()
      expect(queryClient.getQueryData(['event-sliders', 'en'])).toEqual(['public'])
      expect(fetch.mock.calls.map(([url]) => String(url))).toEqual([
        'http://localhost:8000/api/auth/csrf/session',
        'http://localhost:8000/api/auth/refresh',
      ]) // The guard never logs out a valid session or makes its own role requests.
    },
  )

  it('malformed /me role fails closed with safe retry and no private layout', async () => {
    fetch
      .mockResolvedValueOnce(json({ csrf_token: 'recovered' }))
      .mockResolvedValueOnce(json({ ...user, role: 'SUPERADMIN' }))
    renderApp('/admin/users', true)
    expect(await screen.findByRole('heading', { name: 'Administration access' })).toBeVisible()
    expectNoPrivateLayout()
    expect(useAuthStore.getState()).toMatchObject({ status: 'unauthenticated', role: null })
    expect(screen.getByRole('alert')).toHaveTextContent(
      'The session could not be verified. Please try again.',
    )
    expect(screen.getByRole('alert')).not.toHaveTextContent('SUPERADMIN')
    expect(fetch).toHaveBeenCalledTimes(2)
  })
})
