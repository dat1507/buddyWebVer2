import { StrictMode } from 'react'
import { QueryClientProvider } from '@tanstack/react-query'
import { act, cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { MemoryRouter, useLocation, useNavigate } from 'react-router'
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
function NavigationProbe() {
  const { pathname, search, hash, state } = useLocation()
  const navigate = useNavigate()
  return (
    <>
      <div data-testid="location">{JSON.stringify({ pathname, search, hash, state })}</div>
      <button onClick={() => void navigate(-1)}>Test back</button>
      <button onClick={() => void navigate('/')}>Test home</button>
    </>
  )
}

describe('AUTH-022 actual User login + client + guarded routing', () => {
  let fetch: ReturnType<typeof vi.fn<typeof globalThis.fetch>>
  beforeEach(async () => {
    await i18n.changeLanguage('en')
    useAuthStore.getState().resetSession()
    queryClient.setQueryData(['profile', 'own'], completeOwnProfile)
    queryClient.setQueryData(['profile', 'completion'], completeProfileCompletion)
    vi.spyOn(profileClient, 'readOwn').mockResolvedValue(completeOwnProfile)
    vi.spyOn(profileClient, 'readCompletion').mockResolvedValue(completeProfileCompletion)
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
  const renderApp = (
    entry:
      string | { pathname: string; search?: string; hash?: string; state?: unknown } = '/login',
    bootstrap = false,
  ) =>
    render(
      <StrictMode>
        <QueryClientProvider client={queryClient}>
          <MemoryRouter initialEntries={['/', entry]} initialIndex={1}>
            <NavigationProbe />
            {bootstrap ? <SessionBootstrap /> : null}
            <App />
          </MemoryRouter>
        </QueryClientProvider>
      </StrictMode>,
    )
  const location = () =>
    JSON.parse(screen.getByTestId('location').textContent!) as {
      pathname: string
      search: string
      hash: string
      state: unknown
    }
  const expectNoPrivate = () => {
    expect(document.querySelector('[data-layout="user"]')).toBeNull()
    expect(document.querySelector('[data-layout="admin"]')).toBeNull()
  }
  const submit = (language = 'en') => {
    fireEvent.change(
      screen.getByLabelText(language === 'en' ? 'Email address' : 'E-Mail-Adresse'),
      { target: { value: ' student@example.com ' } },
    )
    const password = screen.getByLabelText(language === 'en' ? 'Password' : 'Passwort')
    fireEvent.change(password, { target: { value: 'fixture password' } })
    const form = within(screen.getByRole('main'))
      .getByRole('button', { name: language === 'en' ? 'Sign in' : 'Anmelden' })
      .closest('form')!
    fireEvent.submit(form)
    return { form, password }
  }
  const anonymousLogin = (response: Response | Promise<Response>) =>
    fetch
      .mockResolvedValueOnce(json({}, 401))
      .mockResolvedValueOnce(json({ csrf_token: 'preauth' }))
      .mockReturnValueOnce(Promise.resolve(response))

  it.each([
    ['USER', 'en'],
    ['ADMIN', 'en'],
    ['USER', 'de'],
    ['ADMIN', 'de'],
  ] as const)(
    'verified %s login in %s routes once after response, strips extra fields and clears password',
    async (role, language) => {
      await i18n.changeLanguage(language)
      const login = deferred<Response>()
      anonymousLogin(login.promise)
      renderApp()
      const { form, password } = submit(language)
      fireEvent.submit(form)
      try {
        await waitFor(() => expect(fetch).toHaveBeenCalledTimes(3))
        expect(form).toHaveAttribute('aria-busy', 'true')
        expect(within(form).getByRole('button')).toBeDisabled()
        expect(password).toBeDisabled()
        expect(location().pathname).toBe('/login')
        expectNoPrivate()
        expect(fetch.mock.calls[2][1]).toMatchObject({
          method: 'POST',
          credentials: 'include',
          cache: 'no-store',
          headers: { 'X-CSRF-Token': 'preauth' },
        })
        expect(JSON.parse(fetch.mock.calls[2][1]!.body as string)).toEqual({
          email: user.email,
          password: 'fixture password',
        })
      } finally {
        await act(async () =>
          login.resolve(
            json({
              user: { ...user, role, password: 'discarded fixture', profile: { private: true } },
              csrf_token: 'session',
            }),
          ),
        )
      }
      expect(
        await screen.findByRole('heading', {
          name:
            role === 'USER'
              ? language === 'en'
                ? 'Dashboard'
                : 'Übersicht'
              : language === 'en'
                ? 'Admin overview'
                : 'Administrationsübersicht',
        }),
      ).toBeVisible()
      expect(location()).toEqual({
        pathname: role === 'USER' ? '/user/dashboard' : '/admin/dashboard',
        search: '',
        hash: '',
        state: null,
      })
      expect(password).toHaveValue('')
      expect(useAuthStore.getState().user).toEqual({ ...user, role })
      expect(
        document.querySelector(`[data-layout="${role === 'USER' ? 'admin' : 'user'}"]`),
      ).toBeNull()
      expect(fetch).toHaveBeenCalledTimes(3) // No extra /me, refresh or logout after successful login.
      fireEvent.click(screen.getByRole('button', { name: 'Test back' }))
      expect(
        await screen.findByRole('heading', {
          name: language === 'en' ? /Connect with/ : /Verbinde dich/,
        }),
      ).toBeVisible()
      expect(location().pathname).toBe('/')
    },
  )

  it.each(['USER', 'ADMIN'] as const)(
    'already verified %s visiting /login follows its fixed role route',
    async (role) => {
      useAuthStore.getState().setAuthenticated({ ...user, role })
      renderApp()
      expect(
        await screen.findByRole('heading', {
          name: role === 'USER' ? 'Dashboard' : 'Admin overview',
        }),
      ).toBeVisible()
      expect(fetch).not.toHaveBeenCalled()
    },
  )

  it.each(['unknown', 'loading', 'unauthenticated'] as const)(
    '%s session remains on public login without private rendering',
    (status) => {
      if (status === 'loading') useAuthStore.getState().startLoading()
      if (status === 'unauthenticated') useAuthStore.getState().clearSession()
      renderApp()
      expect(screen.getByRole('heading', { name: 'Welcome back' })).toBeVisible()
      expect(location().pathname).toBe('/login')
      expectNoPrivate()
      expect(fetch).not.toHaveBeenCalled()
    },
  )

  it.each(['https://example.com', '//example.com', '/admin/users'])(
    'ignores destination %s from query/hash/state/stale storage',
    async (destination) => {
      sessionStorage.setItem(
        'auth',
        JSON.stringify({ ...user, role: 'ADMIN', status: 'authenticated' }),
      )
      anonymousLogin(json({ user, csrf_token: 'session' }))
      renderApp({
        pathname: '/login',
        search: '?redirect=' + encodeURIComponent(destination),
        hash: '#ADMIN',
        state: { from: { pathname: destination }, role: 'ADMIN' },
      })
      expectNoPrivate()
      submit()
      expect(await screen.findByRole('heading', { name: 'Dashboard' })).toBeVisible()
      expect(location()).toEqual({ pathname: '/user/dashboard', search: '', hash: '', state: null })
      sessionStorage.removeItem('auth')
    },
  )

  it.each([401, 403, 422, 429, 503])(
    'login %s offers safe manual retry without automatic refresh or success redirect',
    async (status) => {
      anonymousLogin(json({ detail: 'raw private diagnostic' }, status))
      renderApp()
      submit()
      const alert = await screen.findByRole('alert')
      expect(alert).not.toHaveTextContent('raw private diagnostic')
      expect(
        within(screen.getByRole('main')).getByRole('button', { name: 'Try again' }),
      ).toBeEnabled()
      expect(location().pathname).toBe('/login')
      expect(useAuthStore.getState()).toMatchObject({ status: 'unauthenticated', role: null })
      expectNoPrivate()
      expect(fetch).toHaveBeenCalledTimes(3)
    },
  )

  it('network failure displays localized German feedback and never exposes raw diagnostics', async () => {
    await i18n.changeLanguage('de')
    fetch.mockRejectedValueOnce(new Error('raw private diagnostic'))
    renderApp()
    submit('de')
    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Die Anfrage konnte nicht abgeschlossen werden. Prüfe deine Verbindung und versuche es erneut.',
    )
    expect(screen.getByRole('alert')).not.toHaveTextContent('raw private diagnostic')
    expectNoPrivate()
    expect(location().pathname).toBe('/login')
    expect(fetch).toHaveBeenCalledOnce()
  })

  it.each([
    { ...user, role: 'SUPERADMIN' },
    { ...user, role: null },
    { ...user, id: 'invalid' },
    { ...user, email_verified: 'true' },
  ])('malformed sanitized identity cannot trigger role navigation %#', async (payload) => {
    anonymousLogin(json({ user: payload, csrf_token: 'session' }))
    renderApp()
    submit()
    expect(await screen.findByRole('alert')).toBeVisible()
    expect(location().pathname).toBe('/login')
    expectNoPrivate()
    expect(useAuthStore.getState()).toMatchObject({
      status: 'unauthenticated',
      user: null,
      role: null,
    })
  })

  it('manual retry uses fresh CSRF and redirects only after successful retry', async () => {
    anonymousLogin(json({}, 401))
    fetch
      .mockResolvedValueOnce(json({}, 401))
      .mockResolvedValueOnce(json({ csrf_token: 'retry' }))
      .mockResolvedValueOnce(json({ user, csrf_token: 'session' }))
    renderApp()
    submit()
    expect(await screen.findByRole('alert')).toBeVisible()
    fireEvent.click(within(screen.getByRole('main')).getByRole('button', { name: 'Try again' }))
    expect(await screen.findByRole('heading', { name: 'Dashboard' })).toBeVisible()
    expect(fetch.mock.calls[5][1]).toMatchObject({ headers: { 'X-CSRF-Token': 'retry' } })
    expect(fetch).toHaveBeenCalledTimes(6)
  })

  it('login completion after leaving the form retains public navigation and clears detached password', async () => {
    const login = deferred<Response>()
    anonymousLogin(login.promise)
    renderApp()
    const { password } = submit()
    try {
      await waitFor(() => expect(fetch).toHaveBeenCalledTimes(3))
      fireEvent.click(screen.getByRole('button', { name: 'Test home' }))
      expect(await screen.findByRole('heading', { name: /Connect with/ })).toBeVisible()
    } finally {
      await act(async () => login.resolve(json({ user, csrf_token: 'session' })))
    }
    await waitFor(() => expect(useAuthStore.getState().status).toBe('authenticated'))
    expect(location().pathname).toBe('/')
    expect(password).toHaveValue('')
    expectNoPrivate()
  })

  it('logout supersedes pending login and revokes its newly issued session without late navigation', async () => {
    const login = deferred<Response>()
    anonymousLogin(login.promise)
    fetch.mockResolvedValueOnce(new Response(null, { status: 204 }))
    renderApp()
    submit()
    let logout: Promise<void> | undefined
    try {
      await waitFor(() => expect(fetch).toHaveBeenCalledTimes(3))
      act(() => {
        logout = sessionClient.logout()
      })
      expect(useAuthStore.getState().status).toBe('unauthenticated')
    } finally {
      await act(async () => login.resolve(json({ user, csrf_token: 'session' })))
    }
    await act(async () => logout)
    expectNoPrivate()
    expect(location().pathname).toBe('/login')
    expect(useAuthStore.getState()).toMatchObject({
      status: 'unauthenticated',
      user: null,
      role: null,
    })
    expect(fetch.mock.calls.map(([url]) => String(url).split('/auth/')[1])).toEqual([
      'csrf/session',
      'csrf',
      'login',
      'logout',
    ])
  })

  it.each(['USER', 'ADMIN'] as const)(
    'signout then %s login serializes cookies and clears private cache while preserving public sliders',
    async (role) => {
      const logout = deferred<Response>()
      useAuthStore.getState().setAuthenticated(user)
      queryClient.setQueryData(['profile', user.id], { sensitive: true })
      queryClient.setQueryData(['event-sliders', 'en'], ['public'])
      fetch
        .mockResolvedValueOnce(json({ csrf_token: 'old' }))
        .mockReturnValueOnce(logout.promise)
        .mockResolvedValueOnce(json({}, 401))
        .mockResolvedValueOnce(json({ csrf_token: 'preauth' }))
        .mockResolvedValueOnce(
          json({
            user: { ...user, id: 'bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb', role },
            csrf_token: 'new',
          }),
        )
      renderApp('/user/profile')
      fireEvent.click(screen.getByRole('button', { name: 'Sign out' }))
      expect(await screen.findByRole('heading', { name: 'Welcome back' })).toBeVisible()
      try {
        await waitFor(() => expect(fetch).toHaveBeenCalledTimes(2))
        submit()
        expectNoPrivate()
        expect(queryClient.getQueryData(['profile', user.id])).toBeUndefined()
        expect(fetch).toHaveBeenCalledTimes(2) // New cookie mutations wait for the older logout.
      } finally {
        await act(async () => logout.resolve(new Response(null, { status: 204 })))
      }
      expect(
        await screen.findByRole('heading', {
          name: role === 'USER' ? 'Dashboard' : 'Admin overview',
        }),
      ).toBeVisible()
      expect(useAuthStore.getState().user?.id).toBe('bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb')
      expect(queryClient.getQueryData(['profile', user.id])).toBeUndefined()
      expect(queryClient.getQueryData(['event-sliders', 'en'])).toEqual(['public'])
      expect(fetch.mock.calls.map(([url]) => String(url).split('/auth/')[1])).toEqual([
        'csrf/session',
        'logout',
        'csrf/session',
        'csrf',
        'login',
      ])
    },
  )

  it.each(['USER', 'ADMIN'] as const)(
    'reload at /login redirects only after final /me verifies %s',
    async (role) => {
      const me = deferred<Response>()
      fetch.mockResolvedValueOnce(json({ csrf_token: 'recovered' })).mockReturnValueOnce(me.promise)
      renderApp('/login', true)
      try {
        await waitFor(() => expect(fetch).toHaveBeenCalledTimes(2))
        expect(location().pathname).toBe('/login')
        expectNoPrivate()
      } finally {
        await act(async () => me.resolve(json({ ...user, role })))
      }
      expect(
        await screen.findByRole('heading', {
          name: role === 'USER' ? 'Dashboard' : 'Admin overview',
        }),
      ).toBeVisible()
      expect(fetch).toHaveBeenCalledTimes(2)
    },
  )

  it('expired access waits for final /me role before redirecting from login', async () => {
    const me = deferred<Response>()
    fetch
      .mockResolvedValueOnce(json({ csrf_token: 'recovered' }))
      .mockResolvedValueOnce(json({}, 401))
      .mockResolvedValueOnce(json({ user: { ...user, role: 'ADMIN' }, csrf_token: 'rotated' }))
      .mockReturnValueOnce(me.promise)
    renderApp('/login', true)
    try {
      await waitFor(() => expect(fetch).toHaveBeenCalledTimes(4))
      expect(location().pathname).toBe('/login')
      expectNoPrivate()
      expect(useAuthStore.getState().status).toBe('loading')
    } finally {
      await act(async () => me.resolve(json(user)))
    }
    expect(await screen.findByRole('heading', { name: 'Dashboard' })).toBeVisible()
    expect(document.querySelector('[data-layout="admin"]')).toBeNull()
    expect(fetch).toHaveBeenCalledTimes(4)
  })

  it('new login supersedes a held bootstrap /me without navigating from its stale role', async () => {
    const me = deferred<Response>()
    fetch
      .mockResolvedValueOnce(json({ csrf_token: 'recovered' }))
      .mockReturnValueOnce(me.promise)
      .mockResolvedValueOnce(json({}, 401))
      .mockResolvedValueOnce(json({ csrf_token: 'preauth' }))
      .mockResolvedValueOnce(json({ user: { ...user, role: 'ADMIN' }, csrf_token: 'session' }))
    renderApp('/login', true)
    try {
      await waitFor(() => expect(fetch).toHaveBeenCalledTimes(2))
      submit()
      expect(location().pathname).toBe('/login')
      expectNoPrivate()
    } finally {
      await act(async () => me.resolve(json(user)))
    }
    expect(await screen.findByText('Admin overview')).toBeVisible()
    expect(document.querySelector('[data-layout="user"]')).toBeNull()
    expect(fetch).toHaveBeenCalledTimes(5)
  })
})
