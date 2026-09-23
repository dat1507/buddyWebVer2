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
  return <div data-testid="location">{pathname + search + hash}</div>
}

describe('FE-021 guarded App and AUTH-021 session integration', () => {
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
  const expectNoStudentShell = () => {
    expect(
      screen.queryByRole('complementary', { name: 'Student workspace' }),
    ).not.toBeInTheDocument()
    expect(screen.queryByRole('main', { name: 'Student content' })).not.toBeInTheDocument()
  }

  it.each([['/user/profile/edit', 'Edit profile']])(
    'renders a verified USER nested route %s inside one layout main',
    (path, title) => {
      useAuthStore.getState().setAuthenticated(user)
      renderApp(path)
      expect(screen.getByRole('complementary', { name: 'Student workspace' })).toBeVisible()
      expect(within(screen.getByRole('main')).getByRole('heading', { name: title })).toBeVisible()
      expect(screen.getAllByRole('main')).toHaveLength(1)
      expect(screen.getByTestId('location')).toHaveTextContent(path)
      expect(fetch).not.toHaveBeenCalled()
    },
  )

  it.each(['unknown', 'loading'] as const)(
    'never mounts the shell during %s session verification',
    (status) => {
      useAuthStore.setState({ status })
      renderApp('/user/profile/edit')
      expect(screen.getByRole('status')).toHaveTextContent('Checking your session')
      expectNoStudentShell()
      expect(screen.getAllByRole('main')).toHaveLength(1)
    },
  )

  it('redirects anonymous access through the existing guard without rendering the shell', async () => {
    useAuthStore.getState().clearSession()
    renderApp('/user/profile/edit')
    expect(await screen.findByRole('heading', { name: 'Welcome back' })).toBeVisible()
    expect(screen.getByTestId('location')).toHaveTextContent('/login')
    expectNoStudentShell()
  })

  it('does not let ADMIN bypass the USER guard', async () => {
    useAuthStore.getState().setAuthenticated({ ...user, role: 'ADMIN' })
    renderApp('/user/profile/edit')
    expect(await screen.findByRole('heading', { name: /Connect with/ })).toBeVisible()
    expect(screen.getByTestId('location').textContent).toBe('/')
    expectNoStudentShell()
    expect(fetch).not.toHaveBeenCalled()
  })

  it('mounts after reload verification/expired-access refresh and unmounts after logout', async () => {
    let resolveMe!: (response: Response) => void
    const me = new Promise<Response>((resolve) => {
      resolveMe = resolve
    })
    fetch
      .mockResolvedValueOnce(json({ csrf_token: 'recovered' }))
      .mockResolvedValueOnce(json({}, 401))
      .mockResolvedValueOnce(json({ user, csrf_token: 'rotated' }))
      .mockReturnValueOnce(me)
      .mockResolvedValueOnce(new Response(null, { status: 204 }))
    renderApp('/user/profile/edit?view=details#photo', true)
    await waitFor(() => expect(fetch).toHaveBeenCalledTimes(4))
    expectNoStudentShell()
    await act(async () => {
      resolveMe(json(user))
    })
    expect(await screen.findByRole('complementary', { name: 'Student workspace' })).toBeVisible()
    expect(
      within(screen.getByRole('main')).getByRole('heading', { name: 'Edit profile' }),
    ).toBeVisible()
    expect(screen.getAllByRole('main')).toHaveLength(1)
    expect(screen.getByTestId('location')).toHaveTextContent(
      '/user/profile/edit?view=details#photo',
    )
    expect(fetch.mock.calls.map(([url]) => url)).toEqual([
      'http://localhost:8000/api/auth/csrf/session',
      'http://localhost:8000/api/auth/me',
      'http://localhost:8000/api/auth/refresh',
      'http://localhost:8000/api/auth/me',
    ])
    fireEvent.click(screen.getByRole('button', { name: 'Sign out' }))
    expect(await screen.findByRole('heading', { name: 'Welcome back' })).toBeVisible()
    expectNoStudentShell()
    expect(fetch.mock.calls[4]).toEqual([
      'http://localhost:8000/api/auth/logout',
      expect.objectContaining({ method: 'POST', credentials: 'include' }),
    ])
  })
})
