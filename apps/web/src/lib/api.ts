type ApiErrorCode =
  | 'unauthorized'
  | 'forbidden'
  | 'conflict'
  | 'validation'
  | 'rateLimited'
  | 'server'
  | 'network'
  | 'invalidResponse'
  | 'configuration'
  | 'cancelled'
  | 'csrf'

class ApiError extends Error {
  readonly status: number
  readonly code: ApiErrorCode
  readonly retryAfter: number | null

  constructor(status: number, code: ApiErrorCode, retryAfter: number | null = null) {
    // Never retain backend bodies, credentials, cookies or raw fetch diagnostics.
    super(`API request failed (${code}).`)
    this.name = 'ApiError'
    this.status = status
    this.code = code
    this.retryAfter = retryAfter
  }
}

interface JsonRequestOptions {
  method?: 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE'
  body?: unknown
  csrfToken?: string
  signal?: AbortSignal
}

function normalizeApiError(error: unknown): ApiError {
  return error instanceof ApiError ? error : new ApiError(0, 'invalidResponse')
}

async function requestJson(path: string, options: JsonRequestOptions = {}): Promise<unknown> {
  const apiBaseUrl = import.meta.env.VITE_API_URL?.replace(/\/+$/, '')
  if (!apiBaseUrl) {
    throw new ApiError(0, 'configuration')
  }
  if (!/^\/(?!\/)/.test(path)) throw new ApiError(0, 'configuration')
  const method = options.method ?? 'GET'
  if (method !== 'GET' && !options.csrfToken) throw new ApiError(0, 'csrf')
  const controller = new AbortController()
  const abort = () => controller.abort()
  if (options.signal?.aborted) abort()
  options.signal?.addEventListener('abort', abort, { once: true })
  const timeout = setTimeout(abort, 15_000)
  try {
    const response = await fetch(`${apiBaseUrl}${path}`, {
      method,
      credentials: 'include',
      cache: path.startsWith('/auth/') ? 'no-store' : 'default',
      headers: {
        Accept: 'application/json',
        ...(options.body === undefined ? {} : { 'Content-Type': 'application/json' }),
        ...(method === 'GET' ? {} : { 'X-CSRF-Token': options.csrfToken! }),
      },
      body: options.body === undefined ? undefined : JSON.stringify(options.body),
      signal: controller.signal,
    })
    if (!response.ok) {
      const codes: Record<number, ApiErrorCode> = {
        401: 'unauthorized',
        403: 'forbidden',
        409: 'conflict',
        422: 'validation',
        429: 'rateLimited',
      }
      const retry = response.headers.get('Retry-After')
      const retryAfter = retry && /^\d+$/.test(retry) ? Number(retry) : null
      throw new ApiError(response.status, codes[response.status] ?? 'server', retryAfter)
    }
    if (response.status === 204) return undefined
    try {
      return (await response.json()) as unknown
    } catch {
      throw new ApiError(response.status, 'invalidResponse')
    }
  } catch (error) {
    if (error instanceof ApiError) throw error
    throw new ApiError(0, options.signal?.aborted ? 'cancelled' : 'network')
  } finally {
    clearTimeout(timeout)
    options.signal?.removeEventListener('abort', abort)
  }
}

function getJson(path: string, signal?: AbortSignal): Promise<unknown> {
  return requestJson(path, { signal })
}

export { ApiError, getJson, requestJson, normalizeApiError }
export type { ApiErrorCode, JsonRequestOptions }
