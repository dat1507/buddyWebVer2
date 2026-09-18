import { QueryClient } from '@tanstack/react-query'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { createSessionClient } from '@/features/auth/session-client'
import { getJson } from '@/lib/api'
import { useAuthStore } from '@/stores/auth-store'

const user = {
  id: 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa',
  email: 'student@example.com',
  role: 'USER',
  email_verified: false,
}
const admin = { ...user, id: 'bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb', role: 'ADMIN' }
const json = (data: unknown, status = 200) => new Response(JSON.stringify(data), { status })
const session = (account = user, token = 'session-fixture') =>
  json({ user: account, csrf_token: token })
const csrf = (token = 'session-fixture') => json({ csrf_token: token })
function deferred<T>() {
  let resolve!: (value: T) => void
  const promise = new Promise<T>((done) => {
    resolve = done
  })
  return { promise, resolve }
}

describe('AUTH-021 session coordination', () => {
  let cache: QueryClient
  let client: ReturnType<typeof createSessionClient>
  let fetch: ReturnType<typeof vi.fn<typeof globalThis.fetch>>
  beforeEach(() => {
    vi.stubEnv('VITE_API_URL', 'http://localhost:8000/api')
    fetch = vi.fn<typeof globalThis.fetch>()
    vi.stubGlobal('fetch', fetch)
    useAuthStore.getState().resetSession()
    cache = new QueryClient({ defaultOptions: { queries: { retry: false } } })
    client = createSessionClient(cache)
  })
  afterEach(() => {
    cache.clear()
    vi.unstubAllEnvs()
    vi.unstubAllGlobals()
    vi.restoreAllMocks()
    useAuthStore.getState().resetSession()
  })
  const seedCaches = () => {
    cache.setQueryData(['profile', user.id], { private: 'profile' })
    cache.setQueryData(['match', user.id], { private: 'match' })
    cache.setQueryData(['private-media', user.id], { private: 'media' })
    cache.setQueryData(['event-sliders', 'en'], ['public'])
  }
  const expectPrivateCleared = () => {
    expect(cache.getQueryData(['profile', user.id])).toBeUndefined()
    expect(cache.getQueryData(['match', user.id])).toBeUndefined()
    expect(cache.getQueryData(['private-media', user.id])).toBeUndefined()
    expect(cache.getQueryData(['event-sliders', 'en'])).toEqual(['public'])
  }
  const bootstrap = async () => {
    fetch.mockResolvedValueOnce(csrf()).mockResolvedValueOnce(json(user))
    await client.bootstrap()
  }

  it('deduplicates bootstrap and exposes pending before the verified actual role', async () => {
    const recovery = deferred<Response>()
    fetch.mockReturnValueOnce(recovery.promise).mockResolvedValueOnce(json(admin))
    const first = client.bootstrap()
    expect(client.bootstrap()).toBe(first)
    expect(useAuthStore.getState()).toMatchObject({ status: 'loading', user: null, role: null })
    expect(client.useFeedback.getState().pending).toBe(true)
    recovery.resolve(csrf())
    await first
    expect(useAuthStore.getState()).toMatchObject({
      status: 'authenticated',
      user: admin,
      role: 'ADMIN',
    })
    expect(fetch).toHaveBeenCalledTimes(2)
    expect(client.useFeedback.getState()).toMatchObject({ pending: false, error: null })
  })

  it('treats anonymous recovery as unauthenticated without refresh loops', async () => {
    fetch.mockResolvedValueOnce(json({}, 401))
    await client.bootstrap()
    expect(useAuthStore.getState().status).toBe('unauthenticated')
    expect(fetch).toHaveBeenCalledTimes(1)
  })

  it('recovers CSRF before a bounded access-expiry refresh and /me retry', async () => {
    fetch
      .mockResolvedValueOnce(csrf('recovered'))
      .mockResolvedValueOnce(json({}, 401))
      .mockResolvedValueOnce(session(admin, 'rotated'))
      .mockResolvedValueOnce(json(admin))
    await client.bootstrap()
    expect(fetch).toHaveBeenCalledTimes(4)
    expect(fetch.mock.calls[2][1]).toMatchObject({
      method: 'POST',
      headers: { 'X-CSRF-Token': 'recovered' },
    })
    expect(useAuthStore.getState().role).toBe('ADMIN')
  })

  it.each(['refresh', 'retry'])('fails closed when %s remains unauthorized', async (failure) => {
    fetch
      .mockResolvedValueOnce(csrf())
      .mockResolvedValueOnce(json({}, 401))
      .mockResolvedValueOnce(failure === 'refresh' ? json({}, 401) : session())
    if (failure === 'retry') fetch.mockResolvedValueOnce(json({}, 401))
    await client.bootstrap()
    expect(useAuthStore.getState()).toMatchObject({
      status: 'unauthenticated',
      user: null,
      role: null,
    })
    expect(fetch).toHaveBeenCalledTimes(failure === 'refresh' ? 3 : 4)
  })

  it.each([403, 429, 503])(
    'exposes %s as a retryable bootstrap error, then recovers',
    async (status) => {
      fetch.mockResolvedValueOnce(json({}, status))
      await expect(client.bootstrap()).rejects.toMatchObject({ status })
      expect(client.useFeedback.getState()).toMatchObject({ pending: false, error: { status } })
      expect(useAuthStore.getState().user).toBeNull()
      await bootstrap()
      expect(useAuthStore.getState().status).toBe('authenticated')
      expect(client.useFeedback.getState().error).toBeNull()
    },
  )

  it('rejects malformed identity without retaining a stale account or raw diagnostics', async () => {
    useAuthStore.getState().setAuthenticated(user)
    fetch
      .mockResolvedValueOnce(csrf())
      .mockResolvedValueOnce(json({ ...admin, email_verified: 'sensitive' }))
    await expect(client.bootstrap()).rejects.toMatchObject({ code: 'invalidResponse' })
    expect(useAuthStore.getState().user).toBeNull()
    expect(JSON.stringify(client.useFeedback.getState())).not.toContain('sensitive')
  })

  it('fresh-client reload recovers CSRF without touching storage or readable cookies', async () => {
    await bootstrap()
    useAuthStore.getState().resetSession()
    client = createSessionClient(cache)
    const storageGet = vi.spyOn(Storage.prototype, 'getItem')
    const storageSet = vi.spyOn(Storage.prototype, 'setItem')
    const cookieGet = vi.spyOn(document, 'cookie', 'get')
    const cookieSet = vi.spyOn(document, 'cookie', 'set')
    fetch
      .mockResolvedValueOnce(csrf('after-reload'))
      .mockResolvedValueOnce(json(admin))
      .mockResolvedValueOnce(json({ ok: true }))
    await client.bootstrap()
    await client.authenticatedJson('/private/action', { method: 'POST', body: {} })
    expect(fetch.mock.calls[4][1]).toMatchObject({ headers: { 'X-CSRF-Token': 'after-reload' } })
    for (const spy of [storageGet, storageSet, cookieGet, cookieSet])
      expect(spy).not.toHaveBeenCalled()
  })

  it('single-flights concurrent 401 recovery and retries each request once', async () => {
    await bootstrap()
    const rotation = deferred<Response>()
    fetch
      .mockResolvedValueOnce(json({}, 401))
      .mockResolvedValueOnce(json({}, 401))
      .mockReturnValueOnce(rotation.promise)
      .mockResolvedValueOnce(json({ item: 1 }))
      .mockResolvedValueOnce(json({ item: 2 }))
    const requests = [
      client.authenticatedJson('/private/one'),
      client.authenticatedJson('/private/two'),
    ]
    await vi.waitFor(() => expect(fetch).toHaveBeenCalledTimes(5))
    rotation.resolve(session())
    await expect(Promise.all(requests)).resolves.toEqual([{ item: 1 }, { item: 2 }])
    expect(fetch.mock.calls.filter(([url]) => String(url).endsWith('/auth/refresh'))).toHaveLength(
      1,
    )
  })

  it('does not rotate twice when a delayed 401 arrives after another refresh completed', async () => {
    await bootstrap()
    const late = deferred<Response>()
    fetch
      .mockResolvedValueOnce(json({}, 401))
      .mockReturnValueOnce(late.promise)
      .mockResolvedValueOnce(session())
      .mockResolvedValueOnce(json({ ok: true }))
      .mockResolvedValueOnce(json({ ok: true }))
    const first = client.authenticatedJson('/private/one')
    const second = client.authenticatedJson('/private/two')
    await first
    late.resolve(json({}, 401))
    await second
    expect(fetch.mock.calls.filter(([url]) => String(url).endsWith('/auth/refresh'))).toHaveLength(
      1,
    )
  })

  it('clears session on a second protected 401 without recursive refresh', async () => {
    await bootstrap()
    fetch
      .mockResolvedValueOnce(json({}, 401))
      .mockResolvedValueOnce(session())
      .mockResolvedValueOnce(json({}, 401))
    await expect(client.authenticatedJson('/private/one')).rejects.toMatchObject({ status: 401 })
    expect(fetch).toHaveBeenCalledTimes(5)
    expect(useAuthStore.getState().status).toBe('unauthenticated')
  })

  it('clears private queries immediately on logout while preserving the public slider', async () => {
    await bootstrap()
    seedCaches()
    const loggedOut = deferred<Response>()
    fetch.mockReturnValueOnce(loggedOut.promise)
    const work = client.logout()
    expect(useAuthStore.getState().user).toBeNull()
    await vi.waitFor(expectPrivateCleared)
    loggedOut.resolve(new Response(null, { status: 204 }))
    await work
    expect(useAuthStore.getState().status).toBe('unauthenticated')
    fetch.mockResolvedValueOnce(json({ items: [] }))
    await expect(getJson('/event-sliders?locale=en')).resolves.toEqual({ items: [] })
  })

  it('cancels an in-flight meta-marked private query so late data cannot repopulate it', async () => {
    await bootstrap()
    const late = deferred<unknown>()
    const query = cache
      .fetchQuery({
        queryKey: ['avatar', user.id],
        meta: { private: true },
        queryFn: () => late.promise,
      })
      .catch(() => undefined)
    fetch.mockResolvedValueOnce(new Response(null, { status: 204 }))
    await client.logout()
    late.resolve({ private: 'late media' })
    await query
    expect(cache.getQueryData(['avatar', user.id])).toBeUndefined()
  })

  it('account switch revokes the old session before obtaining pre-auth and installing the new role', async () => {
    await bootstrap()
    seedCaches()
    fetch
      .mockResolvedValueOnce(csrf('old'))
      .mockResolvedValueOnce(new Response(null, { status: 204 }))
      .mockResolvedValueOnce(csrf('preauth'))
      .mockResolvedValueOnce(session(admin, 'new'))
    const work = client.login({ email: ' admin@example.com ', password: 'fixture password' })
    expect(useAuthStore.getState().user).toBeNull()
    await work
    expect(fetch.mock.calls.slice(2).map(([url]) => String(url).split('/api')[1])).toEqual([
      '/auth/csrf/session',
      '/auth/logout',
      '/auth/csrf',
      '/auth/login',
    ])
    expect(JSON.parse(fetch.mock.calls[5][1]!.body as string)).toEqual({
      email: 'admin@example.com',
      password: 'fixture password',
    })
    expectPrivateCleared()
    expect(useAuthStore.getState().role).toBe('ADMIN')
  })

  it('invalid credentials fail without attempting refresh or faking authentication', async () => {
    fetch
      .mockResolvedValueOnce(json({}, 401))
      .mockResolvedValueOnce(csrf('preauth'))
      .mockResolvedValueOnce(json({}, 401))
    await expect(
      client.login({ email: user.email, password: 'fixture password' }),
    ).rejects.toMatchObject({ code: 'unauthorized' })
    expect(fetch).toHaveBeenCalledTimes(3)
    expect(useAuthStore.getState().user).toBeNull()
  })

  it('registers only email/password/consent without authenticating', async () => {
    fetch
      .mockResolvedValueOnce(csrf('preauth'))
      .mockResolvedValueOnce(json({ status: 'registered' }, 201))
    await client.register({
      email: ' student@example.com ',
      password: '  fixture password  ',
      consent: true,
    })
    expect(JSON.parse(fetch.mock.calls[1][1]!.body as string)).toEqual({
      email: user.email,
      password: '  fixture password  ',
      consent: true,
    })
    expect(useAuthStore.getState().status).toBe('unknown')
  })

  it.each([409, 422, 503])(
    'registration %s can retry using a fresh pre-auth context',
    async (status) => {
      const data = { email: user.email, password: 'fixture password', consent: true }
      fetch
        .mockResolvedValueOnce(csrf('first'))
        .mockResolvedValueOnce(json({}, status))
        .mockResolvedValueOnce(csrf('second'))
        .mockResolvedValueOnce(json({ status: 'registered' }, 201))
      await expect(client.register(data)).rejects.toMatchObject({ status })
      await client.register(data)
      expect(fetch.mock.calls[3][1]).toMatchObject({ headers: { 'X-CSRF-Token': 'second' } })
    },
  )

  it('recovers an invalid session CSRF once, with a finite retry limit', async () => {
    await bootstrap()
    fetch
      .mockResolvedValueOnce(json({}, 403))
      .mockResolvedValueOnce(csrf('replacement'))
      .mockResolvedValueOnce(json({}, 403))
    await expect(client.refresh()).rejects.toMatchObject({ status: 403 })
    expect(fetch).toHaveBeenCalledTimes(5)
    expect(client.useFeedback.getState().pending).toBe(false)
  })

  it('waits for in-flight rotation before logout and uses the rotated CSRF', async () => {
    await bootstrap()
    const rotated = deferred<Response>()
    fetch
      .mockReturnValueOnce(rotated.promise)
      .mockResolvedValueOnce(new Response(null, { status: 204 }))
    const refreshing = client.refresh().catch((error: unknown) => error)
    await vi.waitFor(() => expect(fetch).toHaveBeenCalledTimes(3))
    const logout = client.logout()
    expect(useAuthStore.getState().user).toBeNull()
    expect(fetch).toHaveBeenCalledTimes(3)
    rotated.resolve(session(user, 'latest'))
    await refreshing
    await logout
    expect(fetch.mock.calls[3][1]).toMatchObject({ headers: { 'X-CSRF-Token': 'latest' } })
    expect(useAuthStore.getState().user).toBeNull()
  })

  it('rejects late bootstrap identity after logout intent', async () => {
    const me = deferred<Response>()
    fetch
      .mockResolvedValueOnce(csrf())
      .mockReturnValueOnce(me.promise)
      .mockResolvedValueOnce(new Response(null, { status: 204 }))
    const boot = client.bootstrap().catch((error: unknown) => error)
    await vi.waitFor(() => expect(fetch).toHaveBeenCalledTimes(2))
    const logout = client.logout()
    me.resolve(json(admin))
    await boot
    await logout
    expect(useAuthStore.getState().user).toBeNull()
  })

  it('logout failure stays locally cleared and exposes retry without claiming success', async () => {
    await bootstrap()
    seedCaches()
    fetch
      .mockResolvedValueOnce(json({}, 503))
      .mockResolvedValueOnce(new Response(null, { status: 204 }))
    await expect(client.logout()).rejects.toMatchObject({ status: 503 })
    expect(client.useFeedback.getState()).toMatchObject({
      action: 'logout',
      pending: false,
      error: { status: 503 },
    })
    expectPrivateCleared()
    await client.logout()
    expect(client.useFeedback.getState().error).toBeNull()
  })

  it('anonymous repeated logout obtains pre-auth CSRF for cookie cleanup', async () => {
    fetch
      .mockResolvedValueOnce(json({}, 401))
      .mockResolvedValueOnce(csrf('preauth'))
      .mockResolvedValueOnce(new Response(null, { status: 204 }))
    await client.logout()
    expect(fetch.mock.calls[2][1]).toMatchObject({ headers: { 'X-CSRF-Token': 'preauth' } })
  })

  it('private mutations recover rejected CSRF once and never loop', async () => {
    await bootstrap()
    fetch
      .mockResolvedValueOnce(json({}, 403))
      .mockResolvedValueOnce(csrf('replacement'))
      .mockResolvedValueOnce(json({}, 403))
    await expect(
      client.authenticatedJson('/private/action', { method: 'POST', body: {} }),
    ).rejects.toMatchObject({ status: 403 })
    expect(fetch).toHaveBeenCalledTimes(5)
    expect(fetch.mock.calls[4][1]).toMatchObject({ headers: { 'X-CSRF-Token': 'replacement' } })
  })

  it('does not return stale private data when account intent changed mid-request', async () => {
    await bootstrap()
    const late = deferred<Response>()
    fetch
      .mockReturnValueOnce(late.promise)
      .mockResolvedValueOnce(new Response(null, { status: 204 }))
    const request = client.authenticatedJson('/private/data').catch((error: unknown) => error)
    await vi.waitFor(() => expect(fetch).toHaveBeenCalledTimes(3))
    await client.logout()
    late.resolve(json({ sensitive: 'previous account' }))
    await expect(request).resolves.toMatchObject({ code: 'cancelled' })
  })

  it('clears private cache on logout intent even while cookie rotation is still in flight', async () => {
    await bootstrap()
    seedCaches()
    const rotated = deferred<Response>()
    fetch
      .mockReturnValueOnce(rotated.promise)
      .mockResolvedValueOnce(new Response(null, { status: 204 }))
    const refreshing = client.refresh().catch(() => undefined)
    await vi.waitFor(() => expect(fetch).toHaveBeenCalledTimes(3))
    const logout = client.logout()
    await vi.waitFor(expectPrivateCleared)
    expect(fetch).toHaveBeenCalledTimes(3)
    rotated.resolve(session())
    await refreshing
    await logout
  })

  it('role changes from refresh clear private cache without removing public content', async () => {
    await bootstrap()
    seedCaches()
    fetch.mockResolvedValueOnce(session({ ...user, role: 'ADMIN' }))
    await client.refresh()
    expect(useAuthStore.getState().role).toBe('ADMIN')
    expectPrivateCleared()
  })

  it('network bootstrap failure ends pending and permits explicit retry', async () => {
    fetch.mockRejectedValueOnce(new Error('private diagnostic'))
    await expect(client.bootstrap()).rejects.toMatchObject({ code: 'network' })
    expect(client.useFeedback.getState().pending).toBe(false)
    await bootstrap()
    expect(useAuthStore.getState().status).toBe('authenticated')
  })
})
