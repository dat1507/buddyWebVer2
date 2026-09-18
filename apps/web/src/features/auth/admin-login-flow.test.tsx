import { StrictMode } from 'react'
import { QueryClientProvider } from '@tanstack/react-query'
import { act, cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { MemoryRouter, useLocation, useNavigate } from 'react-router'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import App from '@/App'
import { sessionClient } from '@/features/auth/session-client'
import { SessionBootstrap } from '@/features/auth/session-controls'
import i18n from '@/i18n'
import { queryClient } from '@/lib/query-client'
import { useAuthStore } from '@/stores/auth-store'

const user = {
  id: 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa',
  email: 'student@example.com',
  role: 'USER',
  email_verified: false,
}
const admin = { ...user, role: 'ADMIN' }
const json = (value: unknown, status = 200) => new Response(JSON.stringify(value), { status })
const revoked = () => new Response(null, { status: 204 })
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
      <button onClick={() => void navigate('/adminLogin')}>Test admin entry</button>
    </>
  )
}

describe('AUTH-023 actual Admin login + client + guarded routing', () => {
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
      return revoked()
    })
    await sessionClient.logout().catch(() => undefined)
    queryClient.clear()
    useAuthStore.getState().resetSession()
    sessionStorage.removeItem('auth')
    vi.unstubAllGlobals()
    vi.unstubAllEnvs()
  })
  const renderApp = (
    entry:
      | string
      | { pathname: string; search?: string; hash?: string; state?: unknown } = '/adminLogin',
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
      screen.getByLabelText(language === 'en' ? 'Admin email address' : 'Admin-E-Mail-Adresse'),
      {
        target: { value: ' student@example.com ' },
      },
    )
    const password = screen.getByLabelText(language === 'en' ? 'Admin password' : 'Admin-Passwort')
    fireEvent.change(password, { target: { value: 'fixture password' } })
    const form = within(screen.getByRole('main'))
      .getByRole('button', {
        name: language === 'en' ? 'Continue to administration' : 'Zur Verwaltung fortfahren',
      })
      .closest('form')!
    fireEvent.submit(form)
    return { form, password }
  }
  const anonymousLogin = (response: Response | Promise<Response>) =>
    fetch
      .mockResolvedValueOnce(json({}, 401))
      .mockResolvedValueOnce(json({ csrf_token: 'preauth' }))
      .mockReturnValueOnce(Promise.resolve(response))
  const expectDenial = async (language = 'en') => {
    await waitFor(() => expect(location().pathname).toBe('/'))
    expect(within(screen.getByRole('main')).getByRole('alert')).toHaveTextContent(
      language === 'en'
        ? 'Not authorized as an administrator.'
        : 'Du bist nicht als Administrator autorisiert.',
    )
    expectNoPrivate()
  }
  const paths = () => fetch.mock.calls.map(([url]) => String(url).split('/auth/')[1])

  it.each(['en', 'de'])(
    'verified ADMIN in %s redirects only after response, clears password and replaces history',
    async (language) => {
      await i18n.changeLanguage(language)
      const login = deferred<Response>()
      anonymousLogin(login.promise)
      renderApp()
      const { form, password } = submit(language)
      fireEvent.submit(form)
      try {
        await waitFor(() => expect(fetch).toHaveBeenCalledTimes(3))
        expect(form).toHaveAttribute('aria-busy', 'true')
        expect(password).toBeDisabled()
        expect(within(form).getByRole('button')).toBeDisabled()
        expect(location().pathname).toBe('/adminLogin')
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
              user: { ...admin, password: 'discarded', profile: { private: true } },
              csrf_token: 'session',
            }),
          ),
        )
      }
      expect(
        await screen.findByRole('heading', {
          level: 1,
          name: language === 'en' ? 'Admin overview' : 'Administrationsübersicht',
        }),
      ).toBeVisible()
      expect(location()).toEqual({
        pathname: '/admin/dashboard',
        search: '',
        hash: '',
        state: null,
      })
      expect(useAuthStore.getState().user).toEqual(admin)
      expect(password).toHaveValue('')
      expect(document.querySelector('[data-layout="user"]')).toBeNull()
      expect(paths()).toEqual(['csrf/session', 'csrf', 'login'])
      fireEvent.click(screen.getByRole('button', { name: 'Test back' }))
      await waitFor(() => expect(location().pathname).toBe('/'))
      expect(screen.queryByRole('alert')).not.toBeInTheDocument()
    },
  )

  it.each(['en', 'de'])(
    'new USER login in %s never installs identity, revokes with session CSRF then denies publicly',
    async (language) => {
      await i18n.changeLanguage(language)
      const logout = deferred<Response>()
      anonymousLogin(json({ user, csrf_token: 'new-session' }))
      fetch.mockReturnValueOnce(logout.promise)
      const authenticatedRoles: string[] = []
      const unsubscribe = useAuthStore.subscribe((state) => {
        if (state.status === 'authenticated') authenticatedRoles.push(state.role)
      })
      queryClient.setQueryData(['profile', user.id], { private: true })
      queryClient.setQueryData(['event-sliders', language], ['public'])
      renderApp()
      const { password } = submit(language)
      try {
        await waitFor(() => expect(fetch).toHaveBeenCalledTimes(4))
        expect(location().pathname).toBe('/adminLogin')
        expect(useAuthStore.getState()).toMatchObject({
          status: 'unauthenticated',
          role: null,
          user: null,
        })
        expectNoPrivate()
        expect(fetch.mock.calls[3][1]).toMatchObject({
          method: 'POST',
          credentials: 'include',
          headers: { 'X-CSRF-Token': 'new-session' },
        })
      } finally {
        await act(async () => logout.resolve(revoked()))
        unsubscribe()
      }
      await expectDenial(language)
      expect(authenticatedRoles).toEqual([])
      expect(password).toHaveValue('')
      expect(queryClient.getQueryData(['profile', user.id])).toBeUndefined()
      expect(queryClient.getQueryData(['event-sliders', language])).toEqual(['public'])
      expect(paths()).toEqual(['csrf/session', 'csrf', 'login', 'logout'])
      fireEvent.click(screen.getByRole('button', { name: 'Test back' }))
      await waitFor(() => expect(location().state).toBeNull())
      expect(location().pathname).toBe('/')
    },
  )

  it.each(['service', 'network'])(
    'failed USER revocation (%s) keeps public denial and offers safe logout retry',
    async (failure) => {
      anonymousLogin(json({ user, csrf_token: 'session' }))
      if (failure === 'service')
        fetch.mockResolvedValueOnce(json({ detail: 'private diagnostic' }, 503))
      else fetch.mockRejectedValueOnce(new Error('private diagnostic'))
      fetch.mockResolvedValueOnce(revoked())
      renderApp()
      submit()
      await expectDenial()
      expect(useAuthStore.getState().status).toBe('unauthenticated')
      const controls = screen.getByRole('complementary', { name: 'Session' })
      expect(within(controls).getByRole('alert')).not.toHaveTextContent('private diagnostic')
      expect(sessionClient.useFeedback.getState()).toMatchObject({
        action: 'logout',
        pending: false,
      })
      fireEvent.click(within(controls).getByRole('button', { name: 'Try again' }))
      await waitFor(() =>
        expect(screen.queryByRole('complementary', { name: 'Session' })).not.toBeInTheDocument(),
      )
      await expectDenial()
      expect(paths()).toEqual(['csrf/session', 'csrf', 'login', 'logout', 'logout'])
      expect(fetch.mock.calls[4][1]).toMatchObject({ headers: { 'X-CSRF-Token': 'session' } })
    },
  )

  it.each([204, 403])(
    'USER cleanup recovers CSRF once; retry %s remains bounded and fail closed',
    async (retryStatus) => {
      anonymousLogin(json({ user, csrf_token: 'stale' }))
      fetch
        .mockResolvedValueOnce(json({}, 403))
        .mockResolvedValueOnce(json({ csrf_token: 'recovered' }))
        .mockResolvedValueOnce(retryStatus === 204 ? revoked() : json({}, retryStatus))
      renderApp()
      submit()
      await expectDenial()
      expect(paths()).toEqual(['csrf/session', 'csrf', 'login', 'logout', 'csrf/session', 'logout'])
      expect(fetch.mock.calls[5][1]).toMatchObject({ headers: { 'X-CSRF-Token': 'recovered' } })
      expect(useAuthStore.getState().status).toBe('unauthenticated')
      expect(sessionClient.useFeedback.getState().error?.status ?? null).toBe(
        retryStatus === 204 ? null : 403,
      )
    },
  )

  it.each(['USER', 'ADMIN'] as const)(
    'previously verified %s entry follows its role without a new login or revocation',
    async (role) => {
      useAuthStore.getState().setAuthenticated({ ...user, role })
      renderApp()
      if (role === 'USER') await expectDenial()
      else expect(await screen.findByText('Admin overview')).toBeVisible()
      expect(useAuthStore.getState()).toMatchObject({ status: 'authenticated', role })
      expect(fetch).not.toHaveBeenCalled()
    },
  )

  it.each(['unknown', 'loading', 'unauthenticated'])(
    '%s remains on the public form without early role routing',
    (status) => {
      if (status === 'loading') useAuthStore.getState().startLoading()
      if (status === 'unauthenticated') useAuthStore.getState().clearSession()
      renderApp()
      expect(screen.getByRole('heading', { name: 'Administration access' })).toBeVisible()
      expect(location().pathname).toBe('/adminLogin')
      expectNoPrivate()
      expect(fetch).not.toHaveBeenCalled()
    },
  )

  it.each([401, 403, 422, 429, 503])(
    'login API %s stays on form with safe manual retry and no logout/refresh',
    async (status) => {
      anonymousLogin(json({ detail: 'private diagnostic' }, status))
      renderApp()
      submit()
      expect(await screen.findByRole('alert')).not.toHaveTextContent('private diagnostic')
      expect(
        within(screen.getByRole('main')).getByRole('button', { name: 'Try again' }),
      ).toBeEnabled()
      expect(location().pathname).toBe('/adminLogin')
      expect(useAuthStore.getState().status).toBe('unauthenticated')
      expectNoPrivate()
      expect(paths()).toEqual(['csrf/session', 'csrf', 'login'])
    },
  )

  it('network error remains localized in German without leaking diagnostics', async () => {
    await i18n.changeLanguage('de')
    fetch.mockRejectedValueOnce(new Error('private diagnostic'))
    renderApp()
    submit('de')
    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Die Anfrage konnte nicht abgeschlossen werden.',
    )
    expect(screen.getByRole('alert')).not.toHaveTextContent('private diagnostic')
    expect(location().pathname).toBe('/adminLogin')
    expectNoPrivate()
  })

  it.each([
    { ...admin, role: 'SUPERADMIN' },
    { ...admin, id: 'invalid' },
  ])('invalid backend identity fails closed without a success redirect %#', async (payload) => {
    anonymousLogin(json({ user: payload, csrf_token: 'session' }))
    renderApp()
    submit()
    expect(await screen.findByRole('alert')).toBeVisible()
    expect(location().pathname).toBe('/adminLogin')
    expectNoPrivate()
    expect(useAuthStore.getState()).toMatchObject({
      status: 'unauthenticated',
      user: null,
      role: null,
    })
  })

  it('failed login manual retry obtains fresh CSRF and installs ADMIN only after success', async () => {
    anonymousLogin(json({}, 401))
    fetch
      .mockResolvedValueOnce(json({}, 401))
      .mockResolvedValueOnce(json({ csrf_token: 'retry' }))
      .mockResolvedValueOnce(json({ user: admin, csrf_token: 'session' }))
    renderApp()
    submit()
    expect(await screen.findByRole('alert')).toBeVisible()
    fireEvent.click(within(screen.getByRole('main')).getByRole('button', { name: 'Try again' }))
    expect(await screen.findByText('Admin overview')).toBeVisible()
    expect(fetch.mock.calls[5][1]).toMatchObject({ headers: { 'X-CSRF-Token': 'retry' } })
    expect(fetch).toHaveBeenCalledTimes(6)
  })

  it.each(['https://example.com', '//example.com', '/user/profile'])(
    'ignores caller destination %s, role state and stale storage',
    async (destination) => {
      sessionStorage.setItem('auth', JSON.stringify({ ...admin, status: 'authenticated' }))
      anonymousLogin(json({ user, csrf_token: 'session' }))
      fetch.mockResolvedValueOnce(revoked())
      renderApp({
        pathname: '/adminLogin',
        search: '?redirect=' + encodeURIComponent(destination),
        hash: '#ADMIN',
        state: { from: destination, role: 'ADMIN' },
      })
      expectNoPrivate()
      submit()
      await expectDenial()
      expect(location()).toEqual({
        pathname: '/',
        search: '',
        hash: '',
        state: { authNotice: 'adminDenied' },
      })
      expect(useAuthStore.getState().user).toBeNull()
    },
  )

  it('landing notice uses only a whitelisted code and never echoes arbitrary router state', () => {
    renderApp({ pathname: '/', state: { authNotice: '<private diagnostic>' } })
    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
    expect(screen.queryByText('<private diagnostic>')).not.toBeInTheDocument()
    expectNoPrivate()
  })

  it.each(['USER', 'ADMIN'])(
    'leaving the form before %s response suppresses late navigation but completes required cleanup',
    async (role) => {
      const login = deferred<Response>()
      anonymousLogin(login.promise)
      if (role === 'USER') fetch.mockResolvedValueOnce(revoked())
      renderApp()
      const { password } = submit()
      try {
        await waitFor(() => expect(fetch).toHaveBeenCalledTimes(3))
        fireEvent.click(screen.getByRole('button', { name: 'Test home' }))
        await waitFor(() => expect(location().pathname).toBe('/'))
      } finally {
        await act(async () =>
          login.resolve(json({ user: { ...user, role }, csrf_token: 'session' })),
        )
      }
      await waitFor(() => expect(sessionClient.useFeedback.getState().pending).toBe(false))
      expect(location()).toEqual({ pathname: '/', search: '', hash: '', state: null })
      expect(password).toHaveValue('')
      expectNoPrivate()
      expect(useAuthStore.getState().status).toBe(
        role === 'ADMIN' ? 'authenticated' : 'unauthenticated',
      )
      expect(paths()).toEqual(
        role === 'ADMIN'
          ? ['csrf/session', 'csrf', 'login']
          : ['csrf/session', 'csrf', 'login', 'logout'],
      )
    },
  )

  it('new ADMIN login supersedes held USER cleanup without stale denial or identity overwrite', async () => {
    const logout = deferred<Response>()
    anonymousLogin(json({ user, csrf_token: 'session' }))
    fetch
      .mockReturnValueOnce(logout.promise)
      .mockResolvedValueOnce(json({}, 401))
      .mockResolvedValueOnce(json({ csrf_token: 'new-preauth' }))
      .mockResolvedValueOnce(
        json({
          user: { ...admin, id: 'bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb' },
          csrf_token: 'new-session',
        }),
      )
    renderApp()
    submit()
    let next: Promise<unknown> | undefined
    try {
      await waitFor(() => expect(fetch).toHaveBeenCalledTimes(4))
      act(() => {
        next = sessionClient.login(
          { email: 'admin@example.com', password: 'next fixture' },
          { requiredRole: 'ADMIN' },
        )
      })
      expectNoPrivate()
      expect(fetch).toHaveBeenCalledTimes(4)
    } finally {
      await act(async () => logout.resolve(revoked()))
    }
    await act(async () => next)
    expect(await screen.findByText('Admin overview')).toBeVisible()
    expect(location().pathname).toBe('/admin/dashboard')
    expect(useAuthStore.getState().user?.id).toBe('bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb')
    expect(screen.queryByText('Not authorized as an administrator.')).not.toBeInTheDocument()
    expect(paths()).toEqual([
      'csrf/session',
      'csrf',
      'login',
      'logout',
      'csrf/session',
      'csrf',
      'login',
    ])
  })

  it('logout supersedes held USER cleanup without a stale denial redirect or restored identity', async () => {
    const cleanup = deferred<Response>()
    anonymousLogin(json({ user, csrf_token: 'session' }))
    fetch
      .mockReturnValueOnce(cleanup.promise)
      .mockResolvedValueOnce(json({}, 401))
      .mockResolvedValueOnce(json({ csrf_token: 'preauth-logout' }))
      .mockResolvedValueOnce(revoked())
    renderApp()
    submit()
    let logout: Promise<void> | undefined
    try {
      await waitFor(() => expect(fetch).toHaveBeenCalledTimes(4))
      act(() => {
        logout = sessionClient.logout()
      })
      expectNoPrivate()
      expect(useAuthStore.getState().status).toBe('unauthenticated')
    } finally {
      await act(async () => cleanup.resolve(revoked()))
    }
    await act(async () => logout)
    expect(location().pathname).toBe('/adminLogin')
    expect(useAuthStore.getState()).toMatchObject({
      status: 'unauthenticated',
      user: null,
      role: null,
    })
    expect(paths()).toEqual([
      'csrf/session',
      'csrf',
      'login',
      'logout',
      'csrf/session',
      'csrf',
      'logout',
    ])
  })

  it('signout then Admin login waits for old family revocation and preserves public cache', async () => {
    const logout = deferred<Response>()
    useAuthStore.getState().setAuthenticated(user)
    queryClient.setQueryData(['profile', user.id], { sensitive: true })
    queryClient.setQueryData(['event-sliders', 'en'], ['public'])
    fetch
      .mockResolvedValueOnce(json({ csrf_token: 'old' }))
      .mockReturnValueOnce(logout.promise)
      .mockResolvedValueOnce(json({}, 401))
      .mockResolvedValueOnce(json({ csrf_token: 'preauth' }))
      .mockResolvedValueOnce(json({ user: admin, csrf_token: 'new' }))
    renderApp('/user/profile')
    fireEvent.click(screen.getByRole('button', { name: 'Sign out' }))
    fireEvent.click(screen.getByRole('button', { name: 'Test admin entry' }))
    try {
      await waitFor(() => expect(fetch).toHaveBeenCalledTimes(2))
      submit()
      expectNoPrivate()
      expect(queryClient.getQueryData(['profile', user.id])).toBeUndefined()
      expect(fetch).toHaveBeenCalledTimes(2)
    } finally {
      await act(async () => logout.resolve(revoked()))
    }
    expect(await screen.findByText('Admin overview')).toBeVisible()
    expect(queryClient.getQueryData(['event-sliders', 'en'])).toEqual(['public'])
    expect(paths()).toEqual(['csrf/session', 'logout', 'csrf/session', 'csrf', 'login'])
  })

  it.each(['USER', 'ADMIN'])('reload redirects only after final /me verifies %s', async (role) => {
    const me = deferred<Response>()
    fetch.mockResolvedValueOnce(json({ csrf_token: 'recovered' })).mockReturnValueOnce(me.promise)
    renderApp('/adminLogin', true)
    try {
      await waitFor(() => expect(fetch).toHaveBeenCalledTimes(2))
      expect(location().pathname).toBe('/adminLogin')
      expectNoPrivate()
    } finally {
      await act(async () => me.resolve(json({ ...user, role })))
    }
    if (role === 'ADMIN') expect(await screen.findByText('Admin overview')).toBeVisible()
    else await expectDenial()
    expect(fetch).toHaveBeenCalledTimes(2)
  })

  it('expired access keeps loading until final /me and never routes using interim refresh ADMIN', async () => {
    const me = deferred<Response>()
    fetch
      .mockResolvedValueOnce(json({ csrf_token: 'recovered' }))
      .mockResolvedValueOnce(json({}, 401))
      .mockResolvedValueOnce(json({ user: admin, csrf_token: 'rotated' }))
      .mockReturnValueOnce(me.promise)
    renderApp('/adminLogin', true)
    try {
      await waitFor(() => expect(fetch).toHaveBeenCalledTimes(4))
      expect(location().pathname).toBe('/adminLogin')
      expect(useAuthStore.getState().status).toBe('loading')
      expectNoPrivate()
    } finally {
      await act(async () => me.resolve(json(user)))
    }
    await expectDenial()
    expect(useAuthStore.getState().role).toBe('USER')
    expect(fetch).toHaveBeenCalledTimes(4)
  })
})
