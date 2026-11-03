import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { chatbotClient } from './chatbot-client'
import { ApiError, requestJson } from '@/lib/api'

// Opaque test text, not university facts; exact Phase 3.3 DTO fields.
const fixtureAnswer = {
  answer: 'Fixture answer.',
  language: 'en',
  status: 'answer',
  supported: true,
  mode: 'local_retrieval',
  sources: [
    {
      entry_id: 'website-register',
      title: 'BuddyWeb guide',
      verification_status: 'verified_code',
      verified_on: '2026-10-22',
      references: [],
    },
  ],
}
const json = (payload: unknown, status = 200, headers = {}) =>
  new Response(JSON.stringify(payload), { status, headers })

describe('public chatbot transport and response trust boundary', () => {
  beforeEach(() => vi.stubEnv('VITE_API_URL', '/api'))
  afterEach(() => {
    vi.unstubAllGlobals()
    vi.unstubAllEnvs()
    vi.useRealTimers()
  })

  it.each(['en', 'de'])(
    'uses the server %s language with no identity, CSRF, history or provider',
    async (language) => {
      const fetch = vi.fn().mockResolvedValue(json({ ...fixtureAnswer, language }))
      vi.stubGlobal('fetch', fetch)
      const result = await chatbotClient.ask('Fixture question?')
      expect(result.language).toBe(language)
      expect(fetch).toHaveBeenCalledOnce()
      expect(fetch).toHaveBeenCalledWith(
        '/api/chatbot/query',
        expect.objectContaining({
          method: 'POST',
          credentials: 'omit',
          cache: 'no-store',
          body: '{"question":"Fixture question?"}',
          headers: { Accept: 'application/json', 'Content-Type': 'application/json' },
        }),
      )
    },
  )

  it('does not exempt any neighboring/private POST from CSRF', async () => {
    const fetch = vi.fn()
    vi.stubGlobal('fetch', fetch)
    for (const path of [
      '/chatbot/query?provider=gemini',
      '/chatbot/query/',
      '/profile',
      '/auth/logout',
    ]) {
      await expect(requestJson(path, { method: 'POST' })).rejects.toMatchObject({ code: 'csrf' })
    }
    expect(fetch).not.toHaveBeenCalled()
  })

  it.each(['', '   ', 'x'.repeat(501), '\u0000', '\r'])(
    'rejects invalid questions locally',
    async (question) => {
      const fetch = vi.fn()
      vi.stubGlobal('fetch', fetch)
      await expect(chatbotClient.ask(question)).rejects.toMatchObject({ code: 'validation' })
      expect(fetch).not.toHaveBeenCalled()
    },
  )

  it('counts Unicode code points and preserves normal EN/DE punctuation/newlines', async () => {
    const fetch = vi.fn().mockImplementation(async () => json(fixtureAnswer))
    vi.stubGlobal('fetch', fetch)
    await chatbotClient.ask('😀'.repeat(500))
    await chatbotClient.ask('Wie geht’s?\nÖffnungszeiten bitte!')
    expect(fetch).toHaveBeenCalledTimes(2)
  })

  it.each([
    { ...fixtureAnswer, sources: undefined },
    { ...fixtureAnswer, language: 'vi' },
    { ...fixtureAnswer, status: 'generated' },
    { ...fixtureAnswer, supported: false },
    { ...fixtureAnswer, internal_prompt: 'private fixture' },
    { ...fixtureAnswer, answer: 'x'.repeat(1801) },
    { ...fixtureAnswer, sources: [{ ...fixtureAnswer.sources[0], verified_on: '2026-02-30' }] },
    null,
  ])('rejects malformed, oversized or inconsistent response contracts', async (payload) => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(json(payload)))
    await expect(chatbotClient.ask('Fixture?')).rejects.toMatchObject({ code: 'invalidResponse' })
  })

  it.each([
    'javascript:alert(1)',
    'http://vgu.edu.vn/',
    'https://evil.invalid/',
    'https://vgu.edu.vn.evil.invalid/',
    'https://name@vgu.edu.vn/',
    'https://vgu.edu.vn/?token=x',
    'https://vgu.edu.vn/#secret',
    'https://vgu.edu.vn:123/',
    'apps/api/private.py',
    'https://vgu.edu.vn/\n',
  ])('rejects unapproved source links: %s', async (url) => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        json({
          ...fixtureAnswer,
          sources: [{ ...fixtureAnswer.sources[0], references: [{ title: 'fixture', url }] }],
        }),
      ),
    )
    await expect(chatbotClient.ask('Fixture?')).rejects.toMatchObject({ code: 'invalidResponse' })
  })

  it('accepts actual official citation fields and vetted public URLs', async () => {
    const payload = {
      ...fixtureAnswer,
      sources: [
        {
          ...fixtureAnswer.sources[0],
          title: 'VGU public information',
          verification_status: 'verified_official',
          references: [{ title: 'VGU', url: 'https://vgu.edu.vn/' }],
        },
      ],
    }
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(json(payload)))
    expect(await chatbotClient.ask('Fixture?')).toEqual(payload)
  })

  it.each([400, 422, 429, 500, 503, 504])(
    'sanitizes HTTP %s without retaining backend messages',
    async (status) => {
      vi.stubGlobal(
        'fetch',
        vi.fn().mockResolvedValue(
          json(
            {
              ...fixtureAnswer,
              answer: 'private diagnostic fixture',
              supported: false,
              sources: [],
              status: 'disabled',
            },
            status,
            { 'Retry-After': '2' },
          ),
        ),
      )
      const error = await chatbotClient.ask('Fixture?').catch((failure: unknown) => failure)
      expect(error).toBeInstanceOf(ApiError)
      expect(error).toMatchObject({ status, retryAfter: 2 })
      expect(JSON.stringify(error)).not.toContain('private diagnostic')
    },
  )

  it('handles invalid JSON and rejects non-JSON responses', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response('<html>fixture</html>')))
    await expect(chatbotClient.ask('Fixture?')).rejects.toMatchObject({ code: 'invalidResponse' })
  })

  it('distinguishes a cancelled request from the eight-second public timeout', async () => {
    vi.useFakeTimers()
    vi.stubGlobal(
      'fetch',
      vi.fn().mockImplementation(
        (_url: string, init: RequestInit) =>
          new Promise((_resolve, reject) =>
            init.signal?.addEventListener('abort', () => reject(new Error('raw fixture')), {
              once: true,
            }),
          ),
      ),
    )
    const controller = new AbortController()
    const cancelled = expect(
      chatbotClient.ask('Fixture?', controller.signal),
    ).rejects.toMatchObject({ code: 'cancelled' })
    controller.abort()
    await cancelled
    const timeout = expect(chatbotClient.ask('Fixture?')).rejects.toMatchObject({ code: 'timeout' })
    await vi.advanceTimersByTimeAsync(8000)
    await timeout
  })
  it('rejects historical contracts that falsely claim verification or use unapproved records', async () => {
    const source = {
      entry_id: 'legacy-laundry',
      title: 'Historical student guide (systemPrompt.txt)',
      verification_status: 'historical_reference',
      verified_on: null,
      references: [],
    }
    const historical = { ...fixtureAnswer, status: 'historical_reference', sources: [source] }
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(json(historical)))
    expect((await chatbotClient.ask('Where is the laundry service?')).status).toBe(
      'historical_reference',
    )
    for (const payload of [
      { ...historical, status: 'answer' },
      { ...historical, supported: false },
      { ...historical, sources: [{ ...source, verified_on: '2026-10-24' }] },
      { ...historical, sources: [{ ...source, entry_id: 'legacy-health' }] },
      { ...historical, sources: [{ ...source, title: 'VGU public information' }] },
      {
        ...historical,
        sources: [{ ...source, references: [{ title: 'Unreviewed', url: 'https://vgu.edu.vn/' }] }],
      },
    ]) {
      vi.stubGlobal('fetch', vi.fn().mockResolvedValue(json(payload)))
      await expect(chatbotClient.ask('Fixture?')).rejects.toMatchObject({ code: 'invalidResponse' })
    }
  })
  it.each(['owner_provided', 'conflicted'])(
    'accepts a canonical %s response with exact source provenance',
    async (status) => {
      const payload = {
        ...fixtureAnswer,
        status,
        sources: [
          {
            entry_id: 'owner-' + 'a'.repeat(20),
            title: 'Owner-provided guide (systemPrompt.txt)',
            verification_status: status,
            verified_on: null,
            references: [],
            provenance: {
              filename: 'systemPrompt.txt',
              sha256: 'b'.repeat(64),
              start_line: 10,
              end_line: 12,
              section: 'Fixture section',
            },
          },
        ],
      }
      vi.stubGlobal('fetch', vi.fn().mockResolvedValue(json(payload)))
      expect((await chatbotClient.ask('Fixture question?')).status).toBe(status)
      for (const source of [
        { ...payload.sources[0], verified_on: '2026-10-24' },
        { ...payload.sources[0], provenance: undefined },
        { ...payload.sources[0], provenance: { ...payload.sources[0].provenance, sha256: 'bad' } },
        {
          ...payload.sources[0],
          provenance: { ...payload.sources[0].provenance, filename: 'C:/private.txt' },
        },
        { ...payload.sources[0], provenance: { ...payload.sources[0].provenance, start_line: 15 } },
        { ...payload.sources[0], title: 'VGU public information' },
      ]) {
        vi.stubGlobal('fetch', vi.fn().mockResolvedValue(json({ ...payload, sources: [source] })))
        await expect(chatbotClient.ask('Fixture?')).rejects.toMatchObject({
          code: 'invalidResponse',
        })
      }
    },
  )

  it('accepts an intent clarification without claiming source support', async () => {
    vi.stubGlobal(
      'fetch',
      vi
        .fn()
        .mockResolvedValue(
          json({ ...fixtureAnswer, status: 'clarification', supported: false, sources: [] }),
        ),
    )
    expect((await chatbotClient.ask('Fixture?')).status).toBe('clarification')
  })
})
