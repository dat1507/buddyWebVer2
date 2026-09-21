import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { act, cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, useLocation } from 'react-router'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import App from '@/App'
import { sessionClient } from '@/features/auth/session-client'
import { SessionBootstrap } from '@/features/auth/session-controls'
import i18n from '@/i18n'
import { ApiError } from '@/lib/api'
import { useAuthStore } from '@/stores/auth-store'
import { completeOwnProfile } from '@/test/profile'

const user = {
  id: 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa',
  email: 'student@example.com',
  role: 'USER' as const,
  email_verified: false,
}
const profile = {
  id: 'bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb',
  full_name: null,
  display_name: null,
  student_type: null,
  nationality: null,
  major: null,
  study_year: null,
  bio: null,
  version: 1,
}
const complete = {
  status: 'COMPLETE' as const,
  percentage: 100,
  missing_fields: [],
  matching_eligible: true,
  reasons: [],
}
const incomplete = {
  status: 'INCOMPLETE' as const,
  percentage: 20,
  missing_fields: ['FULL_NAME', 'STUDENT_TYPE', 'AVATAR', 'INTERESTS', 'LANGUAGES'],
  matching_eligible: false,
  reasons: ['PROFILE_INCOMPLETE'],
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
  const { pathname } = useLocation()
  return <p data-testid="location">{pathname}</p>
}

describe('FE-038 profile readiness routing', () => {
  let client: QueryClient
  let fetch: ReturnType<typeof vi.fn<typeof globalThis.fetch>>

  beforeEach(async () => {
    await i18n.changeLanguage('en')
    useAuthStore.getState().resetSession()
    client = new QueryClient({
      defaultOptions: { queries: { retry: false, staleTime: 30_000 } },
    })
    client.setQueryData(['profile', 'own'], completeOwnProfile)
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
    client.clear()
    useAuthStore.getState().resetSession()
    vi.restoreAllMocks()
    vi.unstubAllGlobals()
    vi.unstubAllEnvs()
  })

  const renderApp = (path: string, bootstrap = false) =>
    render(
      <QueryClientProvider client={client}>
        <MemoryRouter initialEntries={[path]}>
          <LocationProbe />
          {bootstrap ? <SessionBootstrap /> : null}
          <App />
        </MemoryRouter>
      </QueryClientProvider>,
    )

  it('routes incomplete and complete USER sessions from login to the correct destination', async () => {
    const authenticatedJson = vi
      .spyOn(sessionClient, 'authenticatedJson')
      .mockImplementation(async (path) => {
        if (path === '/profile/completion') return incomplete
        if (path === '/profile') return profile
        throw new Error(`Unexpected test path: ${path}`)
      })
    useAuthStore.getState().setAuthenticated(user)
    const incompleteView = renderApp('/login')

    expect(
      await screen.findByRole('heading', { level: 1, name: 'Tell us about yourself' }),
    ).toBeVisible()
    expect(screen.getByTestId('location')).toHaveTextContent('/user/onboarding')
    incompleteView.unmount()
    client.clear()
    client.setQueryData(['profile', 'own'], completeOwnProfile)

    authenticatedJson.mockImplementation(async (path) => {
      if (path === '/profile/completion') return complete
      throw new Error(`Unexpected test path: ${path}`)
    })
    renderApp('/login')

    expect(await screen.findByRole('heading', { name: 'Dashboard' })).toBeVisible()
    expect(screen.getByTestId('location')).toHaveTextContent('/user/dashboard')
  })

  it('lets ADMIN bypass student readiness without requesting profile completion', async () => {
    const authenticatedJson = vi.spyOn(sessionClient, 'authenticatedJson')
    useAuthStore.getState().setAuthenticated({ ...user, role: 'ADMIN' })
    renderApp('/login')

    expect(await screen.findByText('Admin overview')).toBeVisible()
    expect(screen.getByTestId('location')).toHaveTextContent('/admin/dashboard')
    expect(authenticatedJson).not.toHaveBeenCalled()
  })

  it('blocks direct matching entry when the server says the USER is ineligible', async () => {
    vi.spyOn(sessionClient, 'authenticatedJson').mockImplementation(async (path) => {
      if (path === '/profile/completion') {
        return {
          ...complete,
          matching_eligible: false,
          reasons: ['MATCHING_OPT_IN_REQUIRED'],
        }
      }
      throw new Error(`Unexpected test path: ${path}`)
    })
    useAuthStore.getState().setAuthenticated(user)
    renderApp('/user/matching')

    expect(await screen.findByRole('heading', { name: 'Dashboard' })).toBeVisible()
    expect(screen.getByTestId('location')).toHaveTextContent('/user/dashboard')
    expect(screen.queryByText('This area is not available yet.')).not.toBeInTheDocument()
  })

  it('keeps the requested route neutral while readiness is loading', async () => {
    const completion = deferred<unknown>()
    vi.spyOn(sessionClient, 'authenticatedJson').mockReturnValue(completion.promise)
    useAuthStore.getState().setAuthenticated(user)
    renderApp('/user/dashboard')

    expect(screen.getByRole('status')).toHaveTextContent('Checking profile readiness')
    expect(screen.getByTestId('location')).toHaveTextContent('/user/dashboard')
    expect(
      screen.queryByRole('heading', { name: 'Tell us about yourself' }),
    ).not.toBeInTheDocument()

    await act(async () => completion.resolve(complete))
    expect(await screen.findByRole('heading', { name: 'Dashboard' })).toBeVisible()
  })

  it('shows retryable failure in place without treating a network error as incomplete', async () => {
    vi.spyOn(sessionClient, 'authenticatedJson')
      .mockRejectedValueOnce(new ApiError(0, 'network'))
      .mockResolvedValueOnce(complete)
    useAuthStore.getState().setAuthenticated(user)
    renderApp('/user/dashboard')

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'We could not verify where your profile should continue.',
    )
    expect(screen.getByTestId('location')).toHaveTextContent('/user/dashboard')
    expect(
      screen.queryByRole('heading', { name: 'Tell us about yourself' }),
    ).not.toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: 'Try again' }))
    expect(await screen.findByRole('heading', { name: 'Dashboard' })).toBeVisible()
  })

  it('does not request readiness until reload bootstrap has resolved /auth/me', async () => {
    const me = deferred<Response>()
    fetch
      .mockResolvedValueOnce(json({ csrf_token: 'recovered' }))
      .mockReturnValueOnce(me.promise)
      .mockResolvedValueOnce(json(complete))
    renderApp('/user/dashboard', true)

    await waitFor(() => expect(fetch).toHaveBeenCalledTimes(2))
    expect(fetch.mock.calls.map(([url]) => String(url))).toEqual([
      'http://localhost:8000/api/auth/csrf/session',
      'http://localhost:8000/api/auth/me',
    ])
    expect(screen.getByTestId('location')).toHaveTextContent('/user/dashboard')

    await act(async () => me.resolve(json(user)))
    expect(await screen.findByRole('heading', { name: 'Dashboard' })).toBeVisible()
    expect(fetch.mock.calls.map(([url]) => String(url))).toEqual([
      'http://localhost:8000/api/auth/csrf/session',
      'http://localhost:8000/api/auth/me',
      'http://localhost:8000/api/profile/completion',
    ])
  })
})
