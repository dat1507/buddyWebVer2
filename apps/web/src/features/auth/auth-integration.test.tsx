import { QueryClientProvider } from '@tanstack/react-query'
import { act, cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { MemoryRouter } from 'react-router'
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
const mainButton = (name: string) => within(screen.getByRole('main')).getByRole('button', { name })

describe('AUTH-021 actual forms + client + Zustand', () => {
  let fetch: ReturnType<typeof vi.fn<typeof globalThis.fetch>>
  beforeEach(async () => {
    await i18n.changeLanguage('en')
    vi.stubEnv('VITE_API_URL', 'http://localhost:8000/api')
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

    fetch = vi.fn<typeof globalThis.fetch>()
    vi.stubGlobal('fetch', fetch)
  })
  afterEach(async () => {
    cleanup()
    // End the singleton's cookie/CSRF lifecycle before the next test.
    fetch
      .mockReset()
      .mockResolvedValueOnce(json({}, 401))
      .mockResolvedValueOnce(json({ csrf_token: 'cleanup' }))
      .mockResolvedValue(new Response(null, { status: 204 }))
    await act(async () => {
      await sessionClient.logout().catch(() => undefined)
    })
    useAuthStore.getState().resetSession()
    queryClient.clear()
    vi.unstubAllGlobals()
    vi.unstubAllEnvs()
  })
  const renderRoute = (path: string, bootstrap = false) =>
    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter initialEntries={[path]}>
          {bootstrap ? <SessionBootstrap /> : null}
          <App />
        </MemoryRouter>
      </QueryClientProvider>,
    )
  const fillRegister = (password = 'fixture password') => {
    fireEvent.change(screen.getByLabelText('Email address'), { target: { value: user.email } })
    fireEvent.change(screen.getByLabelText('Password'), { target: { value: password } })
    fireEvent.click(screen.getByRole('checkbox'))
  }

  it('submits registration once, exposes pending, and redirects only after real API success', async () => {
    let resolve!: (value: Response) => void
    fetch.mockResolvedValueOnce(json({ csrf_token: 'preauth' })).mockReturnValueOnce(
      new Promise((done) => {
        resolve = done
      }),
    )
    renderRoute('/register')
    fillRegister()
    const form = mainButton('Create student account').closest('form')!
    fireEvent.submit(form)
    fireEvent.submit(form)
    expect(mainButton('Please wait…')).toBeDisabled()
    expect(form).toHaveAttribute('aria-busy', 'true')
    await waitFor(() => expect(fetch).toHaveBeenCalledTimes(2))
    expect(fetch.mock.calls[1][1]).toMatchObject({
      credentials: 'include',
      headers: { 'X-CSRF-Token': 'preauth' },
    })
    expect(JSON.parse(fetch.mock.calls[1][1]!.body as string)).toEqual({
      email: user.email,
      password: 'fixture password',
      consent: true,
    })
    expect(screen.getByRole('heading', { name: 'Create your account' })).toBeVisible()
    await act(async () => {
      resolve(json({ status: 'registered' }, 201))
    })
    expect(await screen.findByRole('heading', { name: 'Welcome back' })).toBeVisible()
    expect(useAuthStore.getState().user).toBeNull()
  })

  it.each([409, 422, 503])(
    'registration %s shows error and retries with fresh CSRF',
    async (status) => {
      fetch
        .mockResolvedValueOnce(json({ csrf_token: 'first' }))
        .mockResolvedValueOnce(json({}, status))
        .mockResolvedValueOnce(json({ csrf_token: 'second' }))
        .mockResolvedValueOnce(json({ status: 'registered' }, 201))
      renderRoute('/register')
      fillRegister()
      fireEvent.click(mainButton('Create student account'))
      expect(await screen.findByRole('alert')).toBeVisible()
      fireEvent.click(mainButton('Try again'))
      expect(await screen.findByRole('heading', { name: 'Welcome back' })).toBeVisible()
      expect(fetch.mock.calls[3][1]).toMatchObject({ headers: { 'X-CSRF-Token': 'second' } })
    },
  )

  it.each(['x'.repeat(7), '😀'.repeat(19)])(
    'validates the actual backend password boundary',
    (password) => {
      renderRoute('/register')
      fillRegister(password)
      fireEvent.click(mainButton('Create student account'))
      expect(screen.getByLabelText('Password')).toHaveFocus()
      expect(screen.getByLabelText('Password')).toHaveAttribute('aria-invalid', 'true')
      expect(fetch).not.toHaveBeenCalled()
    },
  )

  it('does not redirect after a completed request when the registration page has unmounted', async () => {
    let resolve!: (value: Response) => void
    fetch.mockResolvedValueOnce(json({ csrf_token: 'preauth' })).mockReturnValueOnce(
      new Promise((done) => {
        resolve = done
      }),
    )
    const view = renderRoute('/register')
    fillRegister()
    fireEvent.click(mainButton('Create student account'))
    await waitFor(() => expect(fetch).toHaveBeenCalledTimes(2))
    view.unmount()
    await act(async () => {
      resolve(json({ status: 'registered' }, 201))
    })
    expect(screen.queryByRole('heading', { name: 'Welcome back' })).not.toBeInTheDocument()
  })

  it.each(['/login', '/adminLogin'])(
    'login at %s installs the backend role and preserves its task-specific behavior',
    async (path) => {
      const admin = { ...user, role: 'ADMIN' }
      fetch
        .mockResolvedValueOnce(json({}, 401))
        .mockResolvedValueOnce(json({ csrf_token: 'preauth' }))
        .mockResolvedValueOnce(json({ user: admin, csrf_token: 'session' }))
      renderRoute(path)
      const adminPage = path === '/adminLogin'
      fireEvent.change(screen.getByLabelText(adminPage ? 'Admin email address' : 'Email address'), {
        target: { value: user.email },
      })
      fireEvent.change(screen.getByLabelText(adminPage ? 'Admin password' : 'Password'), {
        target: { value: 'fixture password' },
      })
      fireEvent.click(mainButton(adminPage ? 'Continue to administration' : 'Sign in'))
      expect(await screen.findByText('Admin overview')).toBeVisible()
      expect(useAuthStore.getState()).toMatchObject({
        status: 'authenticated',
        user: admin,
        role: 'ADMIN',
      })
      expect(document.querySelector('[data-layout="admin"]')).not.toBeNull()
      expect(JSON.parse(fetch.mock.calls[2][1]!.body as string)).not.toHaveProperty('role')
    },
  )

  it('failed login offers manual retry and never installs a fabricated account', async () => {
    fetch
      .mockResolvedValueOnce(json({}, 401))
      .mockResolvedValueOnce(json({ csrf_token: 'preauth' }))
      .mockResolvedValueOnce(json({}, 401))
      .mockResolvedValueOnce(json({}, 401))
      .mockResolvedValueOnce(json({ csrf_token: 'retry' }))
      .mockResolvedValueOnce(json({ user, csrf_token: 'session' }))
    renderRoute('/login')
    fireEvent.change(screen.getByLabelText('Email address'), { target: { value: user.email } })
    fireEvent.change(screen.getByLabelText('Password'), { target: { value: 'fixture password' } })
    fireEvent.click(mainButton('Sign in'))
    expect(await screen.findByRole('alert')).toBeVisible()
    expect(useAuthStore.getState().user).toBeNull()
    fireEvent.click(mainButton('Try again'))
    expect(await screen.findByRole('heading', { name: 'Edit profile' })).toBeVisible()
    expect(useAuthStore.getState().role).toBe('USER')
  })

  it('bootstrap errors expose retry and successful reload enables actual logout', async () => {
    fetch
      .mockResolvedValueOnce(json({}, 503))
      .mockResolvedValueOnce(json({ csrf_token: 'recovered' }))
      .mockResolvedValueOnce(json(user))
      .mockResolvedValueOnce(new Response(null, { status: 204 }))
    renderRoute('/login', true)
    expect(await screen.findByRole('alert')).toHaveTextContent('The service is unavailable.')
    fireEvent.click(screen.getByRole('button', { name: 'Try again' }))
    const logout = await screen.findByRole('button', { name: 'Sign out' })
    queryClient.setQueryData(['profile', user.id], { sensitive: true })
    queryClient.setQueryData(['event-sliders', 'en'], ['public'])
    fireEvent.click(logout)
    await waitFor(() =>
      expect(screen.queryByRole('button', { name: 'Sign out' })).not.toBeInTheDocument(),
    )
    await waitFor(() => expect(sessionClient.useFeedback.getState().pending).toBe(false))
    expect(useAuthStore.getState().status).toBe('unauthenticated')
    expect(queryClient.getQueryData(['profile', user.id])).toBeUndefined()
    expect(queryClient.getQueryData(['event-sliders', 'en'])).toEqual(['public'])
  })

  it('renders session feedback in German', async () => {
    await i18n.changeLanguage('de')
    fetch.mockResolvedValueOnce(json({}, 503))
    renderRoute('/login', true)
    expect(await screen.findByRole('alert')).toHaveTextContent('Der Dienst ist nicht verfügbar.')
    expect(screen.getByRole('button', { name: 'Erneut versuchen' })).toBeEnabled()
  })
})
