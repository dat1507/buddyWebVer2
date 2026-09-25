import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { ApiError, getJson, requestJson } from '@/lib/api'

describe('credentialed JSON transport', () => {
  beforeEach(() => vi.stubEnv('VITE_API_URL', 'http://localhost:8000/api/'))
  afterEach(() => {
    vi.unstubAllGlobals()
    vi.unstubAllEnvs()
    vi.useRealTimers()
  })

  it('preserves public GETs with cookies, Accept and cancellation, without CSRF', async () => {
    const fetch = vi.fn().mockResolvedValue(new Response(JSON.stringify({ items: [] })))
    vi.stubGlobal('fetch', fetch)
    const controller = new AbortController()
    await expect(getJson('/event-sliders?locale=en', controller.signal)).resolves.toEqual({
      items: [],
    })
    expect(fetch).toHaveBeenCalledWith(
      'http://localhost:8000/api/event-sliders?locale=en',
      expect.objectContaining({
        credentials: 'include',
        cache: 'default',
        method: 'GET',
        headers: { Accept: 'application/json' },
      }),
    )
  })

  it('supports the same-origin API path used by the HTTPS development proxy', async () => {
    vi.stubEnv('VITE_API_URL', '/api')
    const fetch = vi.fn().mockResolvedValue(new Response(JSON.stringify({ status: 'alive' })))
    vi.stubGlobal('fetch', fetch)

    await expect(getJson('/health/live')).resolves.toEqual({ status: 'alive' })
    expect(fetch.mock.calls[0][0]).toBe('/api/health/live')
  })

  it('sends JSON and CSRF for unsafe requests and accepts an empty logout response', async () => {
    const fetch = vi.fn().mockResolvedValue(new Response(null, { status: 204 }))
    vi.stubGlobal('fetch', fetch)
    await expect(
      requestJson('/auth/logout', { method: 'POST', body: {}, csrfToken: 'signed-fixture' }),
    ).resolves.toBeUndefined()
    expect(fetch.mock.calls[0][1]).toMatchObject({
      credentials: 'include',
      cache: 'no-store',
      body: '{}',
      headers: {
        Accept: 'application/json',
        'Content-Type': 'application/json',
        'X-CSRF-Token': 'signed-fixture',
      },
    })
  })

  it('sends an authenticated binary body without JSON serialization', async () => {
    const fetch = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          id: 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa',
          mime_type: 'image/png',
        }),
      ),
    )
    vi.stubGlobal('fetch', fetch)
    const image = new File(['png-bytes'], 'avatar.png', { type: 'image/png' })

    await requestJson('/profile/photos', {
      method: 'POST',
      binaryBody: image,
      contentType: image.type,
      csrfToken: 'signed-fixture',
    })

    expect(fetch.mock.calls[0][1]).toMatchObject({
      credentials: 'include',
      cache: 'default',
      body: image,
      headers: {
        Accept: 'application/json',
        'Content-Type': 'image/png',
        'X-CSRF-Token': 'signed-fixture',
      },
    })
  })

  it('fails before fetch when configuration or CSRF is missing', async () => {
    const fetch = vi.fn()
    vi.stubGlobal('fetch', fetch)
    await expect(requestJson('/auth/register', { method: 'POST' })).rejects.toMatchObject({
      code: 'csrf',
    })
    await expect(
      requestJson('/profile/photos', {
        method: 'POST',
        body: {},
        binaryBody: new Blob(),
        contentType: 'image/png',
        csrfToken: 'signed-fixture',
      }),
    ).rejects.toMatchObject({ code: 'configuration' })
    await expect(getJson('//attacker.example')).rejects.toMatchObject({ code: 'configuration' })
    vi.stubEnv('VITE_API_URL', '')
    await expect(getJson('/auth/me')).rejects.toMatchObject({ code: 'configuration' })
    expect(fetch).not.toHaveBeenCalled()
  })

  it.each([
    [401, 'unauthorized'],
    [403, 'forbidden'],
    [409, 'conflict'],
    [422, 'validation'],
    [429, 'rateLimited'],
    [503, 'server'],
  ])('normalizes %s without retaining a raw backend body', async (status, code) => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify({ detail: 'sensitive fixture input' }), {
          status: Number(status),
          headers: { 'Retry-After': '30' },
        }),
      ),
    )
    const error = await getJson('/auth/me').catch((failure: unknown) => failure)
    expect(error).toBeInstanceOf(ApiError)
    expect(error).toMatchObject({ status, code, retryAfter: 30 })
    expect(JSON.stringify(error)).not.toContain('sensitive')
    expect(String(error)).not.toContain('sensitive')
  })

  it('handles malformed JSON and sanitized network failure', async () => {
    const fetch = vi
      .fn()
      .mockResolvedValueOnce(new Response('not-json'))
      .mockRejectedValueOnce(new Error('sensitive fetch details'))
    vi.stubGlobal('fetch', fetch)
    await expect(getJson('/auth/me')).rejects.toMatchObject({ code: 'invalidResponse' })
    await expect(getJson('/auth/me')).rejects.toMatchObject({
      code: 'network',
      message: 'API request failed (network).',
    })
  })

  it('bounds a stalled request and forwards an external abort', async () => {
    vi.useFakeTimers()
    vi.stubGlobal(
      'fetch',
      vi.fn(
        (_url: string, init: RequestInit) =>
          new Promise((_resolve, reject) => {
            init.signal!.addEventListener('abort', () => reject(new Error('aborted')), {
              once: true,
            })
          }),
      ),
    )
    const timed = expect(getJson('/auth/me')).rejects.toMatchObject({ code: 'network' })
    await vi.advanceTimersByTimeAsync(15_000)
    await timed
    const controller = new AbortController()
    const cancelled = expect(getJson('/auth/me', controller.signal)).rejects.toMatchObject({
      code: 'cancelled',
    })
    controller.abort()
    await cancelled
    expect(vi.getTimerCount()).toBe(0)
  })
})
