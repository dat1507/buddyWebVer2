type ApiErrorCode =
  | 'unauthorized'
  | 'forbidden'
  | 'notFound'
  | 'conflict'
  | 'validation'
  | 'rateLimited'
  | 'server'
  | 'network'
  | 'invalidResponse'
  | 'configuration'
  | 'cancelled'
  | 'csrf'

type InvitationApiErrorReason =
  | 'INVITATION_MESSAGE_TOO_MANY_WORDS'
  | 'INVITATION_MESSAGE_TOO_MANY_CODE_POINTS'
  | 'INVITATION_SELF_NOT_ALLOWED'
  | 'INVITATION_SENDER_INELIGIBLE'
  | 'INVITATION_RECIPIENT_INELIGIBLE'
  | 'INVITATION_PENDING_LIMIT_REACHED'
  | 'INVITATION_PENDING_EXISTS'
  | 'INVITATION_ACTIVE_PAIR_EXISTS'
  | 'INVITATION_ACCEPT_NOT_FOUND'
  | 'INVITATION_ACCEPT_EXPIRED'
  | 'INVITATION_ACCEPT_NOT_PENDING'
  | 'INVITATION_ACCEPT_RECIPIENT_INELIGIBLE'
  | 'INVITATION_ACCEPT_PARTICIPANT_INELIGIBLE'
  | 'INVITATION_ACCEPT_OPPOSITE_TYPES_REQUIRED'
  | 'INVITATION_ACCEPT_ACTIVE_PAIR_EXISTS'
  | 'INVITATION_ACCEPT_STATE_CONFLICT'
  | 'INVITATION_MUTATION_NOT_FOUND'
  | 'INVITATION_MUTATION_EXPIRED'
  | 'INVITATION_MUTATION_INVALID_STATE'

type ApiErrorReason = 'STUDENT_TYPE_LOCKED_ACTIVE_MATCH' | InvitationApiErrorReason

const profileConflictReasons = new Set<ApiErrorReason>(['STUDENT_TYPE_LOCKED_ACTIVE_MATCH'])
const invitationReasons = new Set<ApiErrorReason>([
  'INVITATION_MESSAGE_TOO_MANY_WORDS',
  'INVITATION_MESSAGE_TOO_MANY_CODE_POINTS',
  'INVITATION_SELF_NOT_ALLOWED',
  'INVITATION_SENDER_INELIGIBLE',
  'INVITATION_RECIPIENT_INELIGIBLE',
  'INVITATION_PENDING_LIMIT_REACHED',
  'INVITATION_PENDING_EXISTS',
  'INVITATION_ACTIVE_PAIR_EXISTS',
  'INVITATION_ACCEPT_NOT_FOUND',
  'INVITATION_ACCEPT_EXPIRED',
  'INVITATION_ACCEPT_NOT_PENDING',
  'INVITATION_ACCEPT_RECIPIENT_INELIGIBLE',
  'INVITATION_ACCEPT_PARTICIPANT_INELIGIBLE',
  'INVITATION_ACCEPT_OPPOSITE_TYPES_REQUIRED',
  'INVITATION_ACCEPT_ACTIVE_PAIR_EXISTS',
  'INVITATION_ACCEPT_STATE_CONFLICT',
  'INVITATION_MUTATION_NOT_FOUND',
  'INVITATION_MUTATION_EXPIRED',
  'INVITATION_MUTATION_INVALID_STATE',
])

class ApiError extends Error {
  readonly status: number
  readonly code: ApiErrorCode
  readonly retryAfter: number | null
  readonly reason: ApiErrorReason | null

  constructor(
    status: number,
    code: ApiErrorCode,
    retryAfter: number | null = null,
    reason: ApiErrorReason | null = null,
  ) {
    // Never retain backend bodies, credentials, cookies or raw fetch diagnostics.
    super(`API request failed (${code}).`)
    this.name = 'ApiError'
    this.status = status
    this.code = code
    this.retryAfter = retryAfter
    this.reason = reason
  }
}

interface JsonRequestOptions {
  method?: 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE'
  body?: unknown
  binaryBody?: Blob
  contentType?: string
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
  if (
    (options.body !== undefined && options.binaryBody !== undefined) ||
    (options.binaryBody !== undefined && !options.contentType) ||
    (options.binaryBody === undefined && options.contentType !== undefined)
  ) {
    throw new ApiError(0, 'configuration')
  }
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
        ...(options.binaryBody === undefined ? {} : { 'Content-Type': options.contentType! }),
        ...(method === 'GET' ? {} : { 'X-CSRF-Token': options.csrfToken! }),
      },
      body:
        options.binaryBody ??
        (options.body === undefined ? undefined : JSON.stringify(options.body)),
      signal: controller.signal,
    })
    if (!response.ok) {
      const codes: Record<number, ApiErrorCode> = {
        401: 'unauthorized',
        403: 'forbidden',
        404: 'notFound',
        409: 'conflict',
        422: 'validation',
        429: 'rateLimited',
      }
      const retry = response.headers.get('Retry-After')
      const retryAfter = retry && /^\d+$/.test(retry) ? Number(retry) : null
      let reason: ApiErrorReason | null = null
      const allowedReasons =
        path === '/profile' && response.status === 409
          ? profileConflictReasons
          : path.startsWith('/matching/invitations')
            ? invitationReasons
            : null
      if (allowedReasons) {
        try {
          const payload = (await response.json()) as unknown
          if (
            typeof payload === 'object' &&
            payload !== null &&
            'detail' in payload &&
            typeof payload.detail === 'string' &&
            allowedReasons.has(payload.detail as ApiErrorReason)
          ) {
            reason = payload.detail as ApiErrorReason
          }
        } catch {
          // Unknown or malformed error bodies stay fully sanitized.
        }
      }
      throw new ApiError(response.status, codes[response.status] ?? 'server', retryAfter, reason)
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
export type { ApiErrorCode, ApiErrorReason, InvitationApiErrorReason, JsonRequestOptions }
