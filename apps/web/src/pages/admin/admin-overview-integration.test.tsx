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

describe('ADMIN-003 actual guarded overview and session flow', () => {
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
  const renderApp = (path = '/admin/dashboard', bootstrap = false) =>
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
  const expectNoOverview = () => {
    expect(screen.queryByRole('region', { name: 'Admin overview' })).not.toBeInTheDocument()
    expect(screen.queryByText('Total Users')).not.toBeInTheDocument()
  }

  it.each([
    ['/admin', '/admin/dashboard'],
    ['/admin/dashboard', '/admin/dashboard'],
    ['/admin/dashboard?period=week#summary', '/admin/dashboard?period=week#summary'],
  ])('renders %s in one main without a statistics request', (path, destination) => {
    useAuthStore.getState().setAuthenticated(admin)
    renderApp(path)
    const main = screen.getByRole('main', { name: 'Administrator content' })
    const overview = within(main).getByRole('region', { name: 'Admin overview' })
    expect(within(overview).getAllByRole('term')).toHaveLength(6)
    expect(within(overview).getAllByText('Not available')).toHaveLength(6)
    expect(screen.getAllByRole('main')).toHaveLength(1)
    expect(main.querySelector('main')).toBeNull()
    expect(screen.getByTestId('location').textContent).toBe(destination)
    expect(screen.getByRole('link', { name: 'Overview' })).toHaveAttribute('aria-current', 'page')
    expect(fetch).not.toHaveBeenCalled()
  })

  it.each(['unknown', 'loading'] as const)(
    'does not expose overview metrics during %s',
    (status) => {
      useAuthStore.setState({ status })
      renderApp()
      expect(screen.getByRole('status')).toHaveTextContent('Checking your session')
      expectNoOverview()
    },
  )

  it('redirects anonymous dashboard access to Admin login', async () => {
    useAuthStore.getState().clearSession()
    renderApp()
    expect(await screen.findByRole('heading', { name: 'Administration access' })).toBeVisible()
    expect(screen.getByTestId('location').textContent).toBe('/adminLogin')
    expectNoOverview()
  })

  it('denies USER access while retaining its verified identity', async () => {
    useAuthStore.getState().setAuthenticated({ ...admin, role: 'USER' })
    renderApp()
    expect(await screen.findByRole('heading', { name: /Connect with/ })).toBeVisible()
    expectNoOverview()
    expect(useAuthStore.getState().role).toBe('USER')
    expect(screen.getByTestId('location').textContent).toBe('/')
    expect(fetch).not.toHaveBeenCalled()
  })

  it('switches the actual overview to DE without losing route, shell or session', async () => {
    useAuthStore.getState().setAuthenticated(admin)
    renderApp('/admin/dashboard?period=week#summary')
    const main = screen.getByRole('main', { name: 'Administrator content' })
    const region = screen.getByRole('region', { name: 'Admin overview' })
    const identity = useAuthStore.getState().user
    fireEvent.click(screen.getByRole('button', { name: /Switch to German/ }))
    expect(await screen.findByRole('region', { name: 'Administrationsübersicht' })).toBe(region)
    expect(within(region).getByText('KI-Anfragen heute')).toBeVisible()
    expect(within(region).getAllByText('Nicht verfügbar')).toHaveLength(6)
    expect(screen.getByRole('main', { name: 'Inhalte der Administration' })).toBe(main)
    expect(screen.getByRole('link', { name: 'Übersicht' })).toHaveAttribute('aria-current', 'page')
    expect(screen.getByTestId('location').textContent).toBe('/admin/dashboard?period=week#summary')
    expect(useAuthStore.getState().user).toBe(identity)
    expect(fetch).not.toHaveBeenCalled()
  })

  it('opens Overview from another module and leaves other module scaffolds intact', () => {
    useAuthStore.getState().setAuthenticated(admin)
    renderApp('/admin/users')
    const main = screen.getByRole('main', { name: 'Administrator content' })
    const nav = screen.getByRole('navigation', { name: 'Administrator navigation' })
    fireEvent.click(within(nav).getByRole('link', { name: 'Overview' }))
    expect(within(main).getByRole('region', { name: 'Admin overview' })).toBeVisible()
    fireEvent.click(within(nav).getByRole('link', { name: 'Event Sliders' }))
    expect(within(main).getByRole('heading', { name: 'Event sliders' })).toBeVisible()
    expectNoOverview()
    fireEvent.click(within(nav).getByRole('link', { name: 'Overview' }))
    expect(within(main).getAllByRole('definition')).toHaveLength(6)
    expect(screen.getByRole('main', { name: 'Administrator content' })).toBe(main)
    expect(screen.getByRole('navigation', { name: 'Administrator navigation' })).toBe(nav)
    expect(fetch).not.toHaveBeenCalled()
  })

  it.each(['ADMIN', 'USER'])(
    'uses final me role %s after refresh before exposing the overview',
    async (role) => {
      let resolveMe!: (response: Response) => void
      const finalMe = new Promise<Response>((resolve) => {
        resolveMe = resolve
      })
      fetch
        .mockResolvedValueOnce(json({ csrf_token: 'session-csrf' }))
        .mockResolvedValueOnce(json({}, 401))
        .mockResolvedValueOnce(json({ user: admin, csrf_token: 'rotated-csrf' }))
        .mockReturnValueOnce(finalMe)
      renderApp('/admin/dashboard?period=week#summary', true)
      await waitFor(() => expect(fetch).toHaveBeenCalledTimes(4))
      expectNoOverview()
      await act(async () => {
        resolveMe(json({ ...admin, role }))
      })
      if (role === 'ADMIN') {
        expect(await screen.findByRole('region', { name: 'Admin overview' })).toBeVisible()
        expect(screen.getByTestId('location').textContent).toBe(
          '/admin/dashboard?period=week#summary',
        )
      } else {
        expect(await screen.findByRole('heading', { name: /Connect with/ })).toBeVisible()
        expectNoOverview()
        expect(useAuthStore.getState().role).toBe('USER')
      }
      expect(fetch.mock.calls.map(([url]) => url)).toEqual([
        'http://localhost:8000/api/auth/csrf/session',
        'http://localhost:8000/api/auth/me',
        'http://localhost:8000/api/auth/refresh',
        'http://localhost:8000/api/auth/me',
      ])
    },
  )

  it('keeps metrics absent when refresh cannot restore the dashboard session', async () => {
    fetch
      .mockResolvedValueOnce(json({ csrf_token: 'session-csrf' }))
      .mockResolvedValueOnce(json({}, 401))
      .mockResolvedValueOnce(json({}, 401))
    renderApp('/admin/dashboard', true)
    expect(await screen.findByRole('heading', { name: 'Administration access' })).toBeVisible()
    expectNoOverview()
    expect(screen.getByTestId('location').textContent).toBe('/adminLogin')
    expect(fetch).toHaveBeenCalledTimes(3)
  })

  it.each([204, 503])('unmounts the overview immediately on logout response %s', async (status) => {
    fetch
      .mockResolvedValueOnce(json({ csrf_token: 'session-csrf' }))
      .mockResolvedValueOnce(json(admin))
      .mockResolvedValueOnce(status === 204 ? new Response(null, { status }) : json({}, status))
    renderApp('/admin/dashboard', true)
    expect(await screen.findByRole('region', { name: 'Admin overview' })).toBeVisible()
    fireEvent.click(screen.getByRole('button', { name: 'Sign out' }))
    expectNoOverview()
    expect(await screen.findByRole('heading', { name: 'Administration access' })).toBeVisible()
    await waitFor(() => expect(fetch).toHaveBeenCalledTimes(3))
    expect(new Headers(fetch.mock.calls[2][1]?.headers).get('X-CSRF-Token')).toBe('session-csrf')
    expect(useAuthStore.getState().user).toBeNull()
  })
})
