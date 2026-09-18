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
const modules = [
  ['Overview', 'dashboard', 'Admin overview'],
  ['Users', 'users', 'User management'],
  ['Matching', 'matching', 'Matching management'],
  ['Events', 'events', 'Event management'],
  ['Event Sliders', 'event-sliders', 'Event sliders'],
  ['Announcements', 'announcements', 'Announcements'],
  ['Knowledge Base', 'knowledge-base', 'Knowledge base'],
  ['Campus', 'campus', 'Campus management'],
  ['Analytics', 'analytics', 'Analytics'],
  ['Audit Log', 'audit-log', 'Audit log'],
  ['Settings', 'settings', 'Admin settings'],
] as const

function LocationProbe() {
  const { pathname, search, hash } = useLocation()
  return <p data-testid="location">{pathname + search + hash}</p>
}

describe('ADMIN-002 guarded App navigation', () => {
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
  const renderApp = (path = '/admin', bootstrap = false) =>
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
  const expectNoMenu = () =>
    expect(
      screen.queryByRole('navigation', { name: 'Administrator navigation' }),
    ).not.toBeInTheDocument()

  it.each(modules)(
    'opens the guarded %s destination through the actual sidebar',
    (label, path, title) => {
      useAuthStore.getState().setAuthenticated(admin)
      renderApp('/admin/settings')
      const nav = screen.getByRole('navigation', { name: 'Administrator navigation' })
      const main = screen.getByRole('main', { name: 'Administrator content' })
      const link = within(nav).getByRole('link', { name: label })
      fireEvent.click(link)
      expect(screen.getByTestId('location').textContent).toBe(`/admin/${path}`)
      expect(within(main).getByRole('heading', { name: title })).toBeVisible()
      expect(screen.getAllByRole('main')).toHaveLength(1)
      expect(screen.getByRole('main', { name: 'Administrator content' })).toBe(main)
      expect(screen.getByRole('navigation', { name: 'Administrator navigation' })).toBe(nav)
      expect(link).toHaveAttribute('aria-current', 'page')
      expect(nav.querySelectorAll('[aria-current="page"]')).toHaveLength(1)
      expect(useAuthStore.getState().role).toBe('ADMIN')
      expect(fetch).not.toHaveBeenCalled()
    },
  )

  it('translates the menu with the actual language toggle while preserving route and session', async () => {
    useAuthStore.getState().setAuthenticated(admin)
    renderApp('/admin/event-sliders?view=published#slides')
    const nav = screen.getByRole('navigation', { name: 'Administrator navigation' })
    const user = useAuthStore.getState().user
    fireEvent.click(screen.getByRole('button', { name: /Switch to German/ }))
    expect(await screen.findByRole('navigation', { name: 'Administrationsnavigation' })).toBe(nav)
    const labels = [
      'Übersicht',
      'Benutzer',
      'Zuordnung',
      'Veranstaltungen',
      'Veranstaltungsslider',
      'Mitteilungen',
      'Wissensdatenbank',
      'Campus',
      'Analysen',
      'Audit-Protokoll',
      'Einstellungen',
    ]
    labels.forEach((name) => expect(within(nav).getByRole('link', { name })).toBeVisible())
    expect(within(nav).getByRole('link', { name: 'Veranstaltungsslider' })).toHaveAttribute(
      'aria-current',
      'page',
    )
    expect(screen.getByTestId('location').textContent).toBe(
      '/admin/event-sliders?view=published#slides',
    )
    expect(useAuthStore.getState().user).toBe(user)
    expect(fetch).not.toHaveBeenCalled()
  })

  it.each(['unknown', 'loading'] as const)('hides the new route menu during %s', (status) => {
    useAuthStore.setState({ status })
    renderApp('/admin/event-sliders')
    expect(screen.getByRole('status')).toHaveTextContent('Checking your session')
    expectNoMenu()
  })

  it('redirects anonymous Event Sliders access to Admin login', async () => {
    useAuthStore.getState().clearSession()
    renderApp('/admin/event-sliders')
    expect(await screen.findByRole('heading', { name: 'Administration access' })).toBeVisible()
    expect(screen.getByTestId('location').textContent).toBe('/adminLogin')
    expectNoMenu()
  })

  it('denies a verified USER access to the new Admin route', async () => {
    useAuthStore.getState().setAuthenticated({ ...admin, role: 'USER' })
    renderApp('/admin/event-sliders')
    expect(await screen.findByRole('heading', { name: /Connect with/ })).toBeVisible()
    expect(screen.getByTestId('location').textContent).toBe('/')
    expectNoMenu()
    expect(useAuthStore.getState().role).toBe('USER')
    expect(fetch).not.toHaveBeenCalled()
  })

  it('redirects the Admin index to Overview with exactly one current link', () => {
    useAuthStore.getState().setAuthenticated(admin)
    renderApp()
    const nav = screen.getByRole('navigation', { name: 'Administrator navigation' })
    expect(screen.getByTestId('location').textContent).toBe('/admin/dashboard')
    expect(within(nav).getByRole('link', { name: 'Overview' })).toHaveAttribute(
      'aria-current',
      'page',
    )
    expect(nav.querySelectorAll('[aria-current="page"]')).toHaveLength(1)
  })

  it('restores the deep link menu only after authoritative me verification', async () => {
    let resolveMe!: (response: Response) => void
    const me = new Promise<Response>((resolve) => {
      resolveMe = resolve
    })
    fetch.mockResolvedValueOnce(json({ csrf_token: 'session-csrf' })).mockReturnValueOnce(me)
    renderApp('/admin/event-sliders?view=published#slides', true)
    await waitFor(() => expect(fetch).toHaveBeenCalledTimes(2))
    expectNoMenu()
    await act(async () => {
      resolveMe(json(admin))
    })
    const nav = await screen.findByRole('navigation', { name: 'Administrator navigation' })
    expect(within(nav).getByRole('link', { name: 'Event Sliders' })).toHaveAttribute(
      'aria-current',
      'page',
    )
    expect(screen.getByRole('heading', { name: 'Event sliders' })).toBeVisible()
    expect(screen.getByTestId('location').textContent).toBe(
      '/admin/event-sliders?view=published#slides',
    )
    expect(fetch.mock.calls.map(([url]) => url)).toEqual([
      'http://localhost:8000/api/auth/csrf/session',
      'http://localhost:8000/api/auth/me',
    ])
  })
})
