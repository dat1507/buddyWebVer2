import { StrictMode } from 'react'
import { QueryClientProvider } from '@tanstack/react-query'
import { act, cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { MemoryRouter, useLocation } from 'react-router'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import App from '@/App'
import { sessionClient } from '@/features/auth/session-client'
import { SessionBootstrap } from '@/features/auth/session-controls'
import i18n from '@/i18n'
import { queryClient } from '@/lib/query-client'
import { useAuthStore } from '@/stores/auth-store'

const admin = {
  id: 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa',
  email: 'admin@example.com',
  role: 'ADMIN',
  email_verified: false,
}
const json = (value: unknown, status = 200) => new Response(JSON.stringify(value), { status })

function LocationProbe() {
  const { pathname, search, hash } = useLocation()
  return <p data-testid="location">{pathname + search + hash}</p>
}

describe('ADMIN-001 guarded App and session integration', () => {
  let fetch: ReturnType<typeof vi.fn<typeof globalThis.fetch>>
  beforeEach(async () => {
    await i18n.changeLanguage('en')
    useAuthStore.getState().resetSession()
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
  const expectNoAdminShell = () => {
    expect(
      screen.queryByRole('complementary', { name: 'Administrator workspace' }),
    ).not.toBeInTheDocument()
    expect(screen.queryByRole('main', { name: 'Administrator content' })).not.toBeInTheDocument()
  }

  it.each([
    ['/admin', '/admin/dashboard', 'Admin overview'],
    ['/admin/users?view=details#profile', '/admin/users?view=details#profile', 'User management'],
  ])('renders verified ADMIN route %s with one content main', (path, destination, title) => {
    useAuthStore.getState().setAuthenticated(admin)
    renderApp(path)
    expect(screen.getByRole('complementary', { name: 'Administrator workspace' })).toBeVisible()
    const main = screen.getByRole('main', { name: 'Administrator content' })
    expect(within(main).getByRole('heading', { name: title })).toBeVisible()
    expect(screen.getAllByRole('main')).toHaveLength(1)
    expect(main.querySelector('main')).toBeNull()
    expect(screen.getByTestId('location').textContent).toBe(destination)
    expect(screen.queryByRole('navigation', { name: 'Student navigation' })).not.toBeInTheDocument()
    expect(fetch).not.toHaveBeenCalled()
  })

  it.each(['unknown', 'loading'] as const)('does not mount the shell during %s', (status) => {
    useAuthStore.setState({ status })
    renderApp('/admin/users')
    expect(screen.getByRole('status')).toHaveTextContent('Checking your session')
    expectNoAdminShell()
  })

  it('redirects anonymous access to Admin login without exposing the shell', async () => {
    useAuthStore.getState().clearSession()
    renderApp('/admin/users')
    expect(await screen.findByRole('heading', { name: 'Administration access' })).toBeVisible()
    expect(screen.getByTestId('location').textContent).toBe('/adminLogin')
    expectNoAdminShell()
  })

  it('denies a verified USER while preserving its identity without mounting the Admin shell', async () => {
    useAuthStore.getState().setAuthenticated({ ...admin, role: 'USER' })
    renderApp('/admin/users')
    expect(await screen.findByRole('heading', { name: /Connect with/ })).toBeVisible()
    expect(screen.getByTestId('location').textContent).toBe('/')
    expectNoAdminShell()
    expect(useAuthStore.getState().role).toBe('USER')
    expect(fetch).not.toHaveBeenCalled()
  })

  it('waits for final me verification after refresh before rendering a reload deep link', async () => {
    let resolveMe!: (response: Response) => void
    const finalMe = new Promise<Response>((resolve) => {
      resolveMe = resolve
    })
    fetch
      .mockResolvedValueOnce(json({ csrf_token: 'session-csrf' }))
      .mockResolvedValueOnce(json({}, 401))
      .mockResolvedValueOnce(json({ user: admin, csrf_token: 'rotated-csrf' }))
      .mockReturnValueOnce(finalMe)
    renderApp('/admin/audit-log?filter=login#latest', true)
    await waitFor(() => expect(fetch).toHaveBeenCalledTimes(4))
    expectNoAdminShell()
    await act(async () => {
      resolveMe(json(admin))
    })
    expect(await screen.findByRole('main', { name: 'Administrator content' })).toBeVisible()
    expect(screen.getByRole('heading', { name: 'Audit log' })).toBeVisible()
    expect(screen.getByTestId('location').textContent).toBe('/admin/audit-log?filter=login#latest')
    expect(fetch.mock.calls.map(([url]) => url)).toEqual([
      'http://localhost:8000/api/auth/csrf/session',
      'http://localhost:8000/api/auth/me',
      'http://localhost:8000/api/auth/refresh',
      'http://localhost:8000/api/auth/me',
    ])
  })

  it.each([204, 503])(
    'removes the shell on CSRF logout even when the response is %s',
    async (status) => {
      fetch
        .mockResolvedValueOnce(json({ csrf_token: 'session-csrf' }))
        .mockResolvedValueOnce(json(admin))
        .mockResolvedValueOnce(status === 204 ? new Response(null, { status }) : json({}, status))
      renderApp('/admin/settings', true)
      expect(await screen.findByRole('main', { name: 'Administrator content' })).toBeVisible()
      fireEvent.click(screen.getByRole('button', { name: 'Sign out' }))
      expectNoAdminShell()
      expect(await screen.findByRole('heading', { name: 'Administration access' })).toBeVisible()
      await waitFor(() => expect(fetch).toHaveBeenCalledTimes(3))
      expect(useAuthStore.getState().user).toBeNull()
      expect(screen.getByTestId('location').textContent).toBe('/adminLogin')
      const logout = fetch.mock.calls[2][1]
      expect(logout).toMatchObject({ method: 'POST', credentials: 'include' })
      expect(new Headers(logout?.headers).get('X-CSRF-Token')).toBe('session-csrf')
    },
  )

  it('uses the shared language toggle without losing its route or nested content', async () => {
    useAuthStore.getState().setAuthenticated(admin)
    renderApp('/admin/users?view=details#profile')
    const main = screen.getByRole('main', { name: 'Administrator content' })
    fireEvent.click(screen.getByRole('button', { name: /Switch to German/ }))
    expect(await screen.findByRole('main', { name: 'Inhalte der Administration' })).toBe(main)
    expect(screen.getByRole('complementary', { name: 'Administrationsbereich' })).toBeVisible()
    expect(within(main).getByRole('heading', { name: 'User management' })).toBeVisible()
    expect(screen.getByTestId('location').textContent).toBe('/admin/users?view=details#profile')
    expect(fetch).not.toHaveBeenCalled()
  })
})
