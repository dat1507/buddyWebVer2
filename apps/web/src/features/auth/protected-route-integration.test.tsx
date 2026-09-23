import { StrictMode } from 'react'
import { QueryClientProvider } from '@tanstack/react-query'
import { act, cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
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

describe('AUTH-005 App routes + AUTH-021 bootstrap/logout', () => {
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
    ['/user', '/login', 'Welcome back'],
    ['/user/dashboard', '/login', 'Welcome back'],
    ['/user/profile?view=details#photo', '/login', 'Welcome back'],
    ['/admin', '/adminLogin', 'Administration access'],
    ['/admin/dashboard', '/adminLogin', 'Administration access'],
    ['/admin/audit-log', '/adminLogin', 'Administration access'],
  ])(
    'anonymous direct navigation to %s redirects to %s before mounting the layout',
    async (path, loginPath, heading) => {
      useAuthStore.getState().clearSession()
      renderApp(path)
      expect(
        await screen.findByRole('heading', { name: path === '/' ? /Connect with/ : heading }),
      ).toBeVisible()
      expect(location()).toBe(loginPath)
      expectNoPrivateLayout()
      expect(fetch).not.toHaveBeenCalled()
    },
  )

  it.each(['/user', '/admin'])(
    'unknown base route %s does not run its dashboard redirect',
    (path) => {
      renderApp(path)
      expect(screen.getByText('Checking your session…')).toBeVisible()
      expect(location()).toBe(path)
      expectNoPrivateLayout()
    },
  )

  it.each([
    ['/', 'Connect with VGU Buddy'],
    ['/login', 'Welcome back'],
    ['/register', 'Create your account'],
    ['/adminLogin', 'Administration access'],
  ])('public route %s remains reachable while session is unknown', async (path, heading) => {
    renderApp(path)
    expect(
      await screen.findByRole('heading', { name: path === '/' ? /Connect with/ : heading }),
    ).toBeVisible()
    expect(location()).toBe(path)
    expect(screen.queryByText('Checking your session…')).not.toBeInTheDocument()
  })

  it.each([
    ['/user', '/user/profile/edit', 'USER', 'Edit profile'],
    ['/admin', '/admin/dashboard', 'ADMIN', 'Admin overview'],
  ])(
    'verified identity at %s keeps the existing dashboard index navigation',
    async (path, dashboard, role, title) => {
      useAuthStore.getState().setAuthenticated({ ...user, role })
      renderApp(path)
      expect(await screen.findByRole('heading', { name: title })).toBeVisible()
      expect(location()).toBe(dashboard)
      expect(fetch).not.toHaveBeenCalled()
    },
  )

  it('reload verification deduplicates StrictMode bootstrap and retains the deep link until /me succeeds', async () => {
    const recovery = deferred<Response>()
    fetch.mockReturnValueOnce(recovery.promise).mockResolvedValueOnce(json(user))
    renderApp('/user/profile/edit?view=details#photo', true)
    expect(screen.getByText('Checking your session…')).toBeVisible()
    expectNoPrivateLayout()
    expect(location()).toBe('/user/profile/edit?view=details#photo')
    await waitFor(() => expect(fetch).toHaveBeenCalledOnce())
    await act(async () => recovery.resolve(json({ csrf_token: 'recovered' })))
    expect(await screen.findByRole('heading', { name: 'Edit profile' })).toBeVisible()
    expect(location()).toBe('/user/profile/edit?view=details#photo')
    expect(useAuthStore.getState().role).toBe('USER')
    expect(fetch.mock.calls.map(([url]) => String(url))).toEqual([
      'http://localhost:8000/api/auth/csrf/session',
      'http://localhost:8000/api/auth/me',
    ])
  })

  it.each([200, 401])(
    'expired access remains neutral until the retried /me resolves with %s',
    async (meStatus) => {
      const me = deferred<Response>()
      fetch
        .mockResolvedValueOnce(json({ csrf_token: 'recovered' }))
        .mockResolvedValueOnce(json({}, 401))
        .mockResolvedValueOnce(json({ user, csrf_token: 'rotated' }))
        .mockReturnValueOnce(me.promise)
      renderApp('/user/settings', true)
      try {
        await waitFor(() => expect(fetch).toHaveBeenCalledTimes(4))
        expect(screen.getByText('Checking your session…')).toBeVisible()
        expect(useAuthStore.getState().status).toBe('loading')
        expectNoPrivateLayout()
        expect(location()).toBe('/user/settings')
      } finally {
        await act(async () => me.resolve(json(user, meStatus)))
      }
      if (meStatus === 200) {
        expect(await screen.findByRole('heading', { name: 'Settings' })).toBeVisible()
        expect(location()).toBe('/user/settings')
      } else {
        expect(await screen.findByRole('heading', { name: 'Welcome back' })).toBeVisible()
        expectNoPrivateLayout()
        expect(location()).toBe('/login')
      }
      expect(fetch).toHaveBeenCalledTimes(4)
    },
  )

  it('rejected refresh redirects only after bounded verification fails', async () => {
    fetch
      .mockResolvedValueOnce(json({ csrf_token: 'recovered' }))
      .mockResolvedValueOnce(json({}, 401))
      .mockResolvedValueOnce(json({}, 401))
    renderApp('/admin/users', true)
    expect(screen.getByText('Checking your session…')).toBeVisible()
    expect(await screen.findByRole('heading', { name: 'Administration access' })).toBeVisible()
    expect(location()).toBe('/adminLogin')
    expectNoPrivateLayout()
    expect(fetch).toHaveBeenCalledTimes(3)
  })

  it('bootstrap storage failure fails closed and keeps safe retry feedback on the login page', async () => {
    fetch.mockResolvedValueOnce(json({}, 503))
    renderApp('/user/profile', true)
    expect(await screen.findByRole('heading', { name: 'Welcome back' })).toBeVisible()
    expect(screen.getByRole('alert')).toHaveTextContent('The service is unavailable.')
    expect(screen.getByRole('button', { name: 'Try again' })).toBeEnabled()
    expectNoPrivateLayout()
    expect(fetch).toHaveBeenCalledOnce()
  })

  it('logout immediately removes the protected layout and private cache before backend completion', async () => {
    const logout = deferred<Response>()
    fetch
      .mockResolvedValueOnce(json({ csrf_token: 'recovered' }))
      .mockReturnValueOnce(logout.promise)
    useAuthStore.getState().setAuthenticated(user)
    queryClient.setQueryData(['profile', user.id], { sensitive: true })
    queryClient.setQueryData(['event-sliders', 'en'], ['public'])
    renderApp('/user/profile/edit')
    fireEvent.click(screen.getByRole('button', { name: 'Sign out' }))
    expect(await screen.findByRole('heading', { name: 'Welcome back' })).toBeVisible()
    expectNoPrivateLayout()
    await waitFor(() => expect(fetch).toHaveBeenCalledTimes(2))
    expect(queryClient.getQueryData(['profile', user.id])).toBeUndefined()
    expect(queryClient.getQueryData(['event-sliders', 'en'])).toEqual(['public'])
    await act(async () => logout.resolve(new Response(null, { status: 204 })))
    await waitFor(() => expect(sessionClient.useFeedback.getState().pending).toBe(false))
    expect(location()).toBe('/login')
    expect(useAuthStore.getState().status).toBe('unauthenticated')
  })
})
