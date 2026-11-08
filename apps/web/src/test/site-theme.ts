import { vi } from 'vitest'

export function stubFetchWithDefaultTheme(fetch: typeof globalThis.fetch) {
  const themeUrl = `${import.meta.env.VITE_API_URL?.replace(/\/+$/, '')}/public/site-theme`
  const fetchWithTheme: typeof globalThis.fetch = (input, init) => {
    // Keep the anonymous theme read out of the caller's request and response sequence.
    if (input === themeUrl && init?.method === 'GET' && init.credentials === 'omit') {
      return Promise.resolve(Response.json({ theme: 'default' }))
    }
    return fetch(input, init)
  }
  vi.stubGlobal('fetch', fetchWithTheme)
}
