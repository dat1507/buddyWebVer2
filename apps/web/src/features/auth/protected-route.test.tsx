import { useEffect } from 'react'
import { act, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes, useLocation, useNavigate } from 'react-router'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { ProtectedRoute } from '@/features/auth/protected-route'
import i18n from '@/i18n'
import { useAuthStore } from '@/stores/auth-store'

const user = {
  id: 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa',
  email: 'student@example.com',
  role: 'USER',
  email_verified: false,
}
const deepLink = '/private/profile?view=details#photo'

function LocationProbe() {
  const { pathname, search, hash, state } = useLocation()
  return <div data-testid="location">{JSON.stringify({ pathname, search, hash, state })}</div>
}

function LoginProbe() {
  const navigate = useNavigate()
  return (
    <>
      <h1>Sign in</h1>
      <button type="button" onClick={() => void navigate(-1)}>
        Back
      </button>
    </>
  )
}

describe('AUTH-005 ProtectedRoute with actual Zustand and router', () => {
  const mounted = vi.fn()
  const unmounted = vi.fn()
  function PrivateContent() {
    useEffect(() => {
      mounted()
      return () => unmounted()
    }, [])
    return <h1>Private profile</h1>
  }
  const renderGuard = (loginPath?: '/login' | '/adminLogin') =>
    render(
      <MemoryRouter initialEntries={['/start', deepLink]} initialIndex={1}>
        <LocationProbe />
        <Routes>
          <Route path="/start" element={<h1>Previous public page</h1>} />
          <Route path="/login" element={<LoginProbe />} />
          <Route path="/adminLogin" element={<LoginProbe />} />
          <Route element={<ProtectedRoute loginPath={loginPath} />}>
            <Route path="/private/:id" element={<PrivateContent />} />
          </Route>
        </Routes>
      </MemoryRouter>,
    )
  const location = () =>
    JSON.parse(screen.getByTestId('location').textContent!) as {
      pathname: string
      search: string
      hash: string
      state: unknown
    }

  beforeEach(async () => {
    await i18n.changeLanguage('en')
    useAuthStore.getState().resetSession()
    mounted.mockClear()
    unmounted.mockClear()
  })
  afterEach(() => {
    vi.restoreAllMocks()
    vi.unstubAllGlobals()
    useAuthStore.getState().resetSession()
  })

  it.each(['unknown', 'loading'])(
    '%s waits without mounting private content or redirecting',
    (status) => {
      if (status === 'loading') useAuthStore.getState().startLoading()
      renderGuard()
      expect(screen.getByRole('status')).toHaveTextContent('Checking your session…')
      expect(screen.getByRole('main')).toHaveAttribute('aria-busy', 'true')
      expect(location()).toMatchObject({
        pathname: '/private/profile',
        search: '?view=details',
        hash: '#photo',
      })
      expect(screen.queryByRole('heading', { name: 'Sign in' })).not.toBeInTheDocument()
      expect(mounted).not.toHaveBeenCalled()
    },
  )

  it('renders neutral German pending copy', async () => {
    await i18n.changeLanguage('de')
    renderGuard()
    expect(screen.getByRole('status')).toHaveTextContent('Deine Sitzung wird überprüft…')
    expect(mounted).not.toHaveBeenCalled()
  })

  it.each(['USER', 'ADMIN'])('renders verified %s identity through the nested outlet', (role) => {
    useAuthStore.getState().setAuthenticated({ ...user, role })
    renderGuard()
    expect(screen.getByRole('heading', { name: 'Private profile' })).toBeVisible()
    expect(screen.queryByRole('status')).not.toBeInTheDocument()
    expect(mounted).toHaveBeenCalledOnce()
    expect(location().pathname).toBe('/private/profile')
  })

  it.each(['/login', '/adminLogin'] as const)(
    'redirects confirmed anonymous identity to %s and preserves the internal destination',
    async (loginPath) => {
      useAuthStore.getState().clearSession()
      renderGuard(loginPath)
      await screen.findByRole('heading', { name: 'Sign in' })
      expect(location()).toMatchObject({
        pathname: loginPath,
        search: '',
        hash: '',
        state: { from: { pathname: '/private/profile', search: '?view=details', hash: '#photo' } },
      })
      expect(mounted).not.toHaveBeenCalled()
      fireEvent.click(screen.getByRole('button', { name: 'Back' }))
      expect(await screen.findByRole('heading', { name: 'Previous public page' })).toBeVisible()
    },
  )

  it('waits across unknown/loading transitions and mounts only after verification', () => {
    renderGuard()
    act(() => useAuthStore.getState().startLoading())
    expect(mounted).not.toHaveBeenCalled()
    expect(location().pathname).toBe('/private/profile')
    act(() => useAuthStore.getState().setAuthenticated(user))
    expect(screen.getByRole('heading', { name: 'Private profile' })).toBeVisible()
    expect(mounted).toHaveBeenCalledOnce()
  })

  it('unmounts private content when account verification restarts without redirect flicker', () => {
    useAuthStore.getState().setAuthenticated(user)
    renderGuard()
    act(() => useAuthStore.getState().startLoading())
    expect(screen.queryByRole('heading', { name: 'Private profile' })).not.toBeInTheDocument()
    expect(screen.getByRole('status')).toBeVisible()
    expect(unmounted).toHaveBeenCalledOnce()
    expect(location().pathname).toBe('/private/profile')
  })

  it('unmounts immediately and redirects after session clear', async () => {
    useAuthStore.getState().setAuthenticated(user)
    renderGuard()
    act(() => useAuthStore.getState().clearSession())
    expect(screen.queryByRole('heading', { name: 'Private profile' })).not.toBeInTheDocument()
    expect(unmounted).toHaveBeenCalledOnce()
    await waitFor(() => expect(location().pathname).toBe('/login'))
  })

  it('does not initiate bootstrap, read credentials, or accept stale storage as authentication', () => {
    sessionStorage.setItem('auth', JSON.stringify({ ...user, status: 'authenticated' }))
    const readStorage = vi.spyOn(Storage.prototype, 'getItem')
    const readCookie = vi.spyOn(Document.prototype, 'cookie', 'get')
    const fetch = vi.fn()
    vi.stubGlobal('fetch', fetch)
    renderGuard()
    expect(screen.getByRole('status')).toBeVisible()
    expect(mounted).not.toHaveBeenCalled()
    expect(readStorage).not.toHaveBeenCalled()
    expect(readCookie).not.toHaveBeenCalled()
    expect(fetch).not.toHaveBeenCalled()
    sessionStorage.removeItem('auth')
  })
})
