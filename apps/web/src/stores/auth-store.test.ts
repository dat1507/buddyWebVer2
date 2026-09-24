import { act, renderHook } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { SessionUserValidationError } from '@/features/auth/session-user'
import type { UserRole } from '@/features/auth/session-user'
import { useAuthStore } from '@/stores/auth-store'
import type { SessionState, SessionStatus } from '@/stores/auth-store'

const user = {
  id: '11111111-1111-4111-8111-111111111111',
  email: 'student@example.com',
  role: 'USER' as const,
  email_verified: false,
  email_verified_at: null,
}
const states: SessionStatus[] = ['unknown', 'loading', 'authenticated', 'unauthenticated']

function initialize(status: SessionStatus) {
  const actions = useAuthStore.getState()
  actions.resetSession()
  if (status === 'loading') actions.startLoading()
  if (status === 'authenticated') actions.setAuthenticated(user)
  if (status === 'unauthenticated') actions.clearSession()
}

function snapshot(): SessionState {
  const state = useAuthStore.getState()
  if (state.status === 'authenticated') {
    return { status: state.status, user: state.user, role: state.role }
  }
  return { status: state.status, user: state.user, role: state.role }
}

describe('useAuthStore', () => {
  beforeEach(() => {
    useAuthStore.getState().resetSession()
  })

  afterEach(() => {
    act(() => useAuthStore.getState().resetSession())
    vi.restoreAllMocks()
    vi.unstubAllGlobals()
  })

  it('starts unknown, not prematurely unauthenticated or authenticated', () => {
    expect(snapshot()).toEqual({ status: 'unknown', user: null, role: null })
    expect(useAuthStore.getInitialState().status).toBe('unknown')
  })

  it.each<UserRole>(['USER', 'ADMIN'])('atomically establishes only sanitized %s state', (role) => {
    const payload = {
      ...user,
      role,
      password: 'test-only-password',
      access_token: 'test-only-access',
      refresh_token: 'test-only-refresh',
      token: 'test-only-token',
      csrf_token: 'test-only-csrf',
      profile: { phone: 'test-only-private-phone' },
    }
    const changes: SessionState[] = []
    const unsubscribe = useAuthStore.subscribe(() => changes.push(snapshot()))
    useAuthStore.getState().setAuthenticated(payload)
    unsubscribe()
    expect(changes).toEqual([{ status: 'authenticated', user: { ...user, role }, role }])
    expect(snapshot()).toEqual(changes[0])
    expect(Object.keys(useAuthStore.getState()).sort()).toEqual([
      'clearSession',
      'resetSession',
      'role',
      'setAuthenticated',
      'startLoading',
      'status',
      'user',
    ])
    expect(JSON.stringify(useAuthStore.getState())).not.toContain('test-only-')
  })

  it.each(states)('clears old identity when starting loading from %s', (status) => {
    initialize(status)
    useAuthStore.getState().startLoading()
    expect(snapshot()).toEqual({ status: 'loading', user: null, role: null })
  })

  it.each(states)('clears identity and resolves unauthenticated from %s', (status) => {
    initialize(status)
    useAuthStore.getState().clearSession()
    useAuthStore.getState().clearSession()
    expect(snapshot()).toEqual({ status: 'unauthenticated', user: null, role: null })
    expect(useAuthStore.getState().setAuthenticated).toBeTypeOf('function')
  })

  it.each(states)('resets to neutral unknown from %s without removing actions', (status) => {
    initialize(status)
    const actions = useAuthStore.getState()
    actions.resetSession()
    expect(snapshot()).toEqual({ status: 'unknown', user: null, role: null })
    expect(useAuthStore.getState().setAuthenticated).toBe(actions.setAuthenticated)
    useAuthStore.getState().setAuthenticated(user)
    expect(snapshot().status).toBe('authenticated')
  })

  it('replaces a previous account and derives its role only from the new DTO', () => {
    useAuthStore.getState().setAuthenticated({ ...user, role: 'ADMIN' })
    const other = {
      ...user,
      id: '22222222-2222-4222-8222-222222222222',
      email: 'other@example.com',
    }
    useAuthStore.getState().setAuthenticated(other)
    expect(snapshot()).toEqual({ status: 'authenticated', user: other, role: 'USER' })
  })

  it.each([null, { ...user, role: 'SUPERADMIN' }, { ...user, email_verified: 'true' }])(
    'fails closed on invalid data instead of retaining a prior ADMIN (%#)',
    (payload) => {
      useAuthStore.getState().setAuthenticated({ ...user, role: 'ADMIN' })
      expect(() => useAuthStore.getState().setAuthenticated(payload)).toThrowError(
        SessionUserValidationError,
      )
      expect(snapshot()).toEqual({ status: 'unauthenticated', user: null, role: null })
    },
  )

  it('does not keep caller references that can mutate stored identity', () => {
    const payload = { ...user, role: 'USER' }
    useAuthStore.getState().setAuthenticated(payload)
    payload.role = 'ADMIN'
    payload.email = 'changed@example.com'
    expect(snapshot()).toEqual({ status: 'authenticated', user, role: 'USER' })
    expect(Object.isFrozen(useAuthStore.getState().user)).toBe(true)
  })

  it('notifies React selectors without intermediate inconsistent identity states', () => {
    const { result } = renderHook(() => useAuthStore((state) => state.status))
    expect(result.current).toBe('unknown')
    act(() => useAuthStore.getState().startLoading())
    expect(result.current).toBe('loading')
    act(() => useAuthStore.getState().setAuthenticated(user))
    expect(result.current).toBe('authenticated')
    act(() => useAuthStore.getState().clearSession())
    expect(result.current).toBe('unauthenticated')
    act(() => useAuthStore.getState().resetSession())
    expect(result.current).toBe('unknown')
  })

  it('does not read or write Web Storage, cookies, indexedDB or make API calls', () => {
    const get = vi.spyOn(Storage.prototype, 'getItem').mockImplementation(() => {
      throw new Error('Storage unavailable')
    })
    const set = vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {
      throw new Error('Storage unavailable')
    })
    const remove = vi.spyOn(Storage.prototype, 'removeItem')
    const clear = vi.spyOn(Storage.prototype, 'clear')
    const cookieGet = vi.spyOn(document, 'cookie', 'get')
    const cookieSet = vi.spyOn(document, 'cookie', 'set')
    const fetch = vi.spyOn(globalThis, 'fetch')
    const open = vi.fn(() => {
      throw new Error('IndexedDB unavailable')
    })
    const deleteDatabase = vi.fn()
    vi.stubGlobal('indexedDB', { open, deleteDatabase })
    useAuthStore.getState().startLoading()
    useAuthStore.getState().setAuthenticated(user)
    useAuthStore.getState().clearSession()
    useAuthStore.getState().resetSession()
    for (const spy of [
      get,
      set,
      remove,
      clear,
      cookieGet,
      cookieSet,
      fetch,
      open,
      deleteDatabase,
    ]) {
      expect(spy).not.toHaveBeenCalled()
    }
    expect(useAuthStore).not.toHaveProperty('persist')
  })

  it('a fresh module ignores stale Web Storage and returns to unknown after reload', async () => {
    localStorage.setItem('auth-store', JSON.stringify({ ...user, role: 'ADMIN' }))
    sessionStorage.setItem('auth-store', JSON.stringify({ ...user, role: 'ADMIN' }))
    useAuthStore.getState().setAuthenticated({ ...user, role: 'ADMIN' })
    const storageGet = vi.spyOn(Storage.prototype, 'getItem')
    const cookieGet = vi.spyOn(document, 'cookie', 'get')
    const fetch = vi.spyOn(globalThis, 'fetch')
    const open = vi.fn()
    vi.stubGlobal('indexedDB', { open })
    vi.resetModules()
    const fresh = (await import('@/stores/auth-store')).useAuthStore
    expect(fresh.getState()).toMatchObject({ status: 'unknown', user: null, role: null })
    expect(fresh.getState()).not.toHaveProperty('token')
    expect(storageGet).not.toHaveBeenCalled()
    expect(cookieGet).not.toHaveBeenCalled()
    expect(fetch).not.toHaveBeenCalled()
    expect(open).not.toHaveBeenCalled()
    vi.restoreAllMocks()
    localStorage.removeItem('auth-store')
    sessionStorage.removeItem('auth-store')
  })
})
