import { useEffect } from 'react'
import { act, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes, useLocation, useNavigate } from 'react-router'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { RoleGuard } from '@/features/auth/role-guard'
import type { UserRole } from '@/features/auth/session-user'
import i18n from '@/i18n'
import { useAuthStore } from '@/stores/auth-store'

const user = {
  id: 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa',
  email: 'student@example.com',
  role: 'USER',
  email_verified: false,
}
const deepLink = '/private/profile?next=https://example.com#photo'

function LocationProbe() {
  const { pathname, search, hash, state } = useLocation()
  return <div data-testid="location">{JSON.stringify({ pathname, search, hash, state })}</div>
}
function HomeProbe() {
  const navigate = useNavigate()
  return (
    <>
      <h1>Public home</h1>
      <button type="button" onClick={() => void navigate(-1)}>
        Back
      </button>
    </>
  )
}

describe('AUTH-006 RoleGuard with actual Zustand and router', () => {
  const mounted = vi.fn()
  const unmounted = vi.fn()
  function PrivateContent() {
    useEffect(() => {
      mounted()
      return () => unmounted()
    }, [])
    return <h1>Private profile</h1>
  }
  const renderGuard = (requiredRole: UserRole, loginPath?: '/login' | '/adminLogin') =>
    render(
      <MemoryRouter initialEntries={['/start', deepLink]} initialIndex={1}>
        <LocationProbe />
        <Routes>
          <Route path="/" element={<HomeProbe />} />
          <Route path="/start" element={<h1>Previous public page</h1>} />
          <Route path="/login" element={<h1>User sign in</h1>} />
          <Route path="/adminLogin" element={<h1>Admin sign in</h1>} />
          <Route element={<RoleGuard requiredRole={requiredRole} loginPath={loginPath} />}>
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

  it.each([
    ['USER', 'unknown'],
    ['USER', 'loading'],
    ['ADMIN', 'unknown'],
    ['ADMIN', 'loading'],
  ] as const)('%s guard stays neutral for %s without mounting or redirecting', (role, status) => {
    if (status === 'loading') useAuthStore.getState().startLoading()
    renderGuard(role)
    expect(screen.getByRole('status')).toHaveTextContent('Checking your session…')
    expect(screen.getByRole('main')).toHaveAttribute('aria-busy', 'true')
    expect(location()).toMatchObject({
      pathname: '/private/profile',
      search: '?next=https://example.com',
      hash: '#photo',
    })
    expect(mounted).not.toHaveBeenCalled()
  })

  it('reuses German pending copy for admin verification', async () => {
    await i18n.changeLanguage('de')
    renderGuard('ADMIN')
    expect(screen.getByRole('status')).toHaveTextContent('Deine Sitzung wird überprüft…')
    expect(mounted).not.toHaveBeenCalled()
  })

  it.each(['USER', 'ADMIN'] as const)('mounts only verified matching %s identity', (role) => {
    useAuthStore.getState().setAuthenticated({ ...user, role })
    renderGuard(role)
    expect(screen.getByRole('heading', { name: 'Private profile' })).toBeVisible()
    expect(mounted).toHaveBeenCalledOnce()
    expect(location().pathname).toBe('/private/profile')
  })

  it.each([
    ['USER', 'ADMIN'],
    ['ADMIN', 'USER'],
  ] as const)(
    'denies %s access to %s without logout or an unsafe redirect',
    async (role, required) => {
      useAuthStore.getState().setAuthenticated({ ...user, role })
      renderGuard(required)
      expect(await screen.findByRole('heading', { name: 'Public home' })).toBeVisible()
      expect(mounted).not.toHaveBeenCalled()
      expect(location()).toEqual({ pathname: '/', search: '', hash: '', state: null })
      expect(useAuthStore.getState()).toMatchObject({ status: 'authenticated', role })
      fireEvent.click(screen.getByRole('button', { name: 'Back' }))
      expect(await screen.findByRole('heading', { name: 'Previous public page' })).toBeVisible()
    },
  )

  it.each([
    ['USER', '/login', 'User sign in'],
    ['ADMIN', '/adminLogin', 'Admin sign in'],
  ] as const)(
    'anonymous %s requests delegate to ProtectedRoute',
    async (role, loginPath, heading) => {
      useAuthStore.getState().clearSession()
      renderGuard(role, loginPath)
      expect(await screen.findByRole('heading', { name: heading })).toBeVisible()
      expect(location()).toMatchObject({
        pathname: loginPath,
        state: {
          from: {
            pathname: '/private/profile',
            search: '?next=https://example.com',
            hash: '#photo',
          },
        },
      })
      expect(mounted).not.toHaveBeenCalled()
    },
  )

  it('denies only after unknown/loading resolves to a mismatched role', async () => {
    renderGuard('ADMIN')
    act(() => useAuthStore.getState().startLoading())
    expect(location().pathname).toBe('/private/profile')
    act(() => useAuthStore.getState().setAuthenticated(user))
    expect(await screen.findByRole('heading', { name: 'Public home' })).toBeVisible()
    expect(mounted).not.toHaveBeenCalled()
  })

  it.each(['USER', 'ADMIN'] as const)(
    'unmounts %s private content immediately on a role change',
    async (role) => {
      useAuthStore.getState().setAuthenticated({ ...user, role })
      renderGuard(role)
      act(() =>
        useAuthStore
          .getState()
          .setAuthenticated({ ...user, role: role === 'USER' ? 'ADMIN' : 'USER' }),
      )
      expect(screen.queryByRole('heading', { name: 'Private profile' })).not.toBeInTheDocument()
      expect(unmounted).toHaveBeenCalledOnce()
      await waitFor(() => expect(location().pathname).toBe('/'))
    },
  )

  it('unmounts during re-verification and redirects to login only after session clear', async () => {
    useAuthStore.getState().setAuthenticated({ ...user, role: 'ADMIN' })
    renderGuard('ADMIN', '/adminLogin')
    act(() => useAuthStore.getState().startLoading())
    expect(screen.getByRole('status')).toBeVisible()
    expect(unmounted).toHaveBeenCalledOnce()
    expect(location().pathname).toBe('/private/profile')
    act(() => useAuthStore.getState().clearSession())
    expect(await screen.findByRole('heading', { name: 'Admin sign in' })).toBeVisible()
    expect(mounted).toHaveBeenCalledOnce()
  })

  it('does not restore a role from storage, read cookies, or initiate bootstrap/logout', () => {
    sessionStorage.setItem(
      'auth',
      JSON.stringify({ ...user, role: 'ADMIN', status: 'authenticated' }),
    )
    const readStorage = vi.spyOn(Storage.prototype, 'getItem')
    const readCookie = vi.spyOn(Document.prototype, 'cookie', 'get')
    const fetch = vi.fn()
    vi.stubGlobal('fetch', fetch)
    renderGuard('ADMIN')
    expect(screen.getByRole('status')).toBeVisible()
    expect(mounted).not.toHaveBeenCalled()
    expect(readStorage).not.toHaveBeenCalled()
    expect(readCookie).not.toHaveBeenCalled()
    expect(fetch).not.toHaveBeenCalled()
    sessionStorage.removeItem('auth')
  })
})
