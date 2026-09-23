import { StrictMode } from 'react'
import { QueryClientProvider } from '@tanstack/react-query'
import { act, cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
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

function LocationProbe() {
  const { pathname, search, hash } = useLocation()
  return <p data-testid="location">{pathname + search + hash}</p>
}

describe('FE-022 navigation in the real guarded App', () => {
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
  const expectNoStudentNavigation = () =>
    expect(screen.queryByRole('navigation', { name: 'Student navigation' })).not.toBeInTheDocument()

  it.each([['/user/profile/edit', 'Edit profile', 'Edit Profile']])(
    'preserves the USER nested route %s and truthful navigation availability',
    (path, title, label) => {
      useAuthStore.getState().setAuthenticated(user)
      renderApp(path)
      const nav = screen.getByRole('navigation', { name: 'Student navigation' })
      expect(
        within(screen.getByRole('complementary', { name: 'Student workspace' })).getByRole(
          'navigation',
        ),
      ).toBe(nav)
      expect(within(screen.getByRole('main')).getByRole('heading', { name: title })).toBeVisible()
      expect(screen.getAllByRole('main')).toHaveLength(1)
      expect(nav.querySelector('[aria-current="page"]')).toHaveTextContent(label)
      expect(within(nav).getByRole('link', { name: 'My Profile' })).toHaveAttribute(
        'href',
        '/user/profile',
      )
      expect(screen.getByTestId('location')).toHaveTextContent(path)
      expect(fetch).not.toHaveBeenCalled()
    },
  )

  it('redirects the retired Dashboard URL to the profile editor', async () => {
    useAuthStore.getState().setAuthenticated(user)
    renderApp('/user/dashboard?view=details#photo')
    expect(await screen.findByRole('heading', { name: 'Edit profile' })).toBeVisible()
    expect(screen.getByTestId('location')).toHaveTextContent('/user/profile/edit')
    expect(screen.queryByText('Dashboard')).not.toBeInTheDocument()
  })

  it.each(['unknown', 'loading'] as const)('does not mount USER navigation during %s', (status) => {
    useAuthStore.setState({ status })
    renderApp('/user/profile/edit')
    expect(screen.getByRole('status')).toHaveTextContent('Checking your session')
    expectNoStudentNavigation()
    expect(fetch).not.toHaveBeenCalled()
  })

  it('keeps anonymous USER navigation behind ProtectedRoute', async () => {
    useAuthStore.getState().clearSession()
    renderApp('/user/profile')
    expect(await screen.findByRole('heading', { name: 'Welcome back' })).toBeVisible()
    expect(screen.getByTestId('location').textContent).toBe('/login')
    expectNoStudentNavigation()
  })

  it('denies ADMIN access to USER navigation while preserving verified identity', async () => {
    useAuthStore.getState().setAuthenticated({ ...user, role: 'ADMIN' })
    renderApp('/user/profile/edit')
    expect(await screen.findByRole('heading', { name: /Connect with/ })).toBeVisible()
    expect(screen.getByTestId('location').textContent).toBe('/')
    expectNoStudentNavigation()
    expect(useAuthStore.getState().role).toBe('ADMIN')
    expect(fetch).not.toHaveBeenCalled()
  })

  it('waits for final reload verification, then removes navigation on CSRF logout', async () => {
    let resolveMe!: (response: Response) => void
    const finalMe = new Promise<Response>((resolve) => {
      resolveMe = resolve
    })
    fetch
      .mockResolvedValueOnce(json({ csrf_token: 'session-csrf' }))
      .mockResolvedValueOnce(json({}, 401))
      .mockResolvedValueOnce(json({ user, csrf_token: 'rotated-csrf' }))
      .mockReturnValueOnce(finalMe)
      .mockResolvedValueOnce(new Response(null, { status: 204 }))
    renderApp('/user/profile/edit?view=details#photo', true)
    await waitFor(() => expect(fetch).toHaveBeenCalledTimes(4))
    expectNoStudentNavigation()
    await act(async () => {
      resolveMe(json(user))
    })
    expect(await screen.findByRole('navigation', { name: 'Student navigation' })).toBeVisible()
    expect(screen.getByTestId('location').textContent).toBe('/user/profile/edit?view=details#photo')
    fireEvent.click(screen.getByRole('button', { name: 'Sign out' }))
    expect(await screen.findByRole('heading', { name: 'Welcome back' })).toBeVisible()
    expectNoStudentNavigation()
    expect(fetch.mock.calls.map(([url]) => url)).toEqual([
      'http://localhost:8000/api/auth/csrf/session',
      'http://localhost:8000/api/auth/me',
      'http://localhost:8000/api/auth/refresh',
      'http://localhost:8000/api/auth/me',
      'http://localhost:8000/api/auth/logout',
    ])
    const logout = fetch.mock.calls[4][1]
    expect(logout).toEqual(expect.objectContaining({ method: 'POST', credentials: 'include' }))
    expect(new Headers(logout?.headers).get('X-CSRF-Token')).toBe('rotated-csrf')
  })

  it('uses the existing language toggle without losing route, active item or Outlet', async () => {
    useAuthStore.getState().setAuthenticated(user)
    renderApp('/user/profile/edit')
    const current = screen
      .getByRole('navigation', { name: 'Student navigation' })
      .querySelector('[aria-current="page"]')
    fireEvent.click(screen.getByRole('button', { name: /Switch to German/ }))
    const nav = await screen.findByRole('navigation', { name: 'Studierendennavigation' })
    expect(nav.querySelector('[aria-current="page"]')).toBe(current)
    expect(current).toHaveTextContent('Profil bearbeiten')
    expect(
      within(screen.getByRole('main')).getByRole('heading', { name: 'Profil bearbeiten' }),
    ).toBeVisible()
    expect(screen.getByTestId('location').textContent).toBe('/user/profile/edit')
    expect(fetch).not.toHaveBeenCalled()
  })
})
