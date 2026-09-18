import type { QueryClient } from '@tanstack/react-query'
import { create } from 'zustand'
import { z } from 'zod'

import { clearPrivateQueries } from '@/features/auth/private-cache'
import { parseSessionUser } from '@/features/auth/session-user'
import type { SessionUser } from '@/features/auth/session-user'
import { ApiError, normalizeApiError, requestJson } from '@/lib/api'
import type { JsonRequestOptions } from '@/lib/api'
import { queryClient } from '@/lib/query-client'
import { useAuthStore } from '@/stores/auth-store'

const csrfSchema = z.object({ csrf_token: z.string().min(1).max(1024) })
const sessionSchema = csrfSchema.extend({ user: z.unknown() })
const registrationSchema = z.object({ status: z.literal('registered') })
type SessionAction = 'bootstrap' | 'login' | 'refresh' | 'logout'
interface SessionFeedback {
  pending: boolean
  action: SessionAction | null
  error: ApiError | null
}
interface Credentials {
  email: string
  password: string
}
interface Registration extends Credentials {
  consent: boolean
}

function createSessionClient(cache: QueryClient) {
  const useFeedback = create<SessionFeedback>()(() => ({
    pending: false,
    action: null,
    error: null,
  }))
  let csrfToken: string | undefined
  let epoch = 0
  let feedbackTicket = 0
  let refreshVersion = 0
  let queue: Promise<void> = Promise.resolve()
  let bootstrapFlight: Promise<void> | undefined
  let refreshFlight: Promise<void> | undefined

  const checkEpoch = (generation: number) => {
    if (generation !== epoch) throw new ApiError(0, 'cancelled')
  }
  const enqueue = <T>(action: () => Promise<T>): Promise<T> => {
    const result = queue.then(action)
    queue = result.then(
      () => undefined,
      () => undefined,
    )
    return result
  }
  const clearIdentity = async () => {
    useAuthStore.getState().clearSession()
    await clearPrivateQueries(cache)
  }
  const recoverCsrf = async () => {
    const result = csrfSchema.safeParse(await requestJson('/auth/csrf/session'))
    if (!result.success) throw new ApiError(200, 'invalidResponse')
    csrfToken = result.data.csrf_token
    return csrfToken
  }
  const preauthCsrf = async () => {
    const result = csrfSchema.safeParse(await requestJson('/auth/csrf'))
    if (!result.success) throw new ApiError(200, 'invalidResponse')
    csrfToken = result.data.csrf_token
    return csrfToken
  }
  // One recovery/retry for a rejected CSRF context; never use pre-auth for a live session.
  const sessionMutation = async (path: string) => {
    const token = csrfToken ?? (await recoverCsrf())
    try {
      return await requestJson(path, { method: 'POST', csrfToken: token })
    } catch (error) {
      if (!(error instanceof ApiError) || error.status !== 403) throw error
      return requestJson(path, { method: 'POST', csrfToken: await recoverCsrf() })
    }
  }
  const installUser = async (payload: unknown, generation: number): Promise<SessionUser> => {
    checkEpoch(generation)
    const user = parseSessionUser(payload)
    const previous = useAuthStore.getState()
    if (previous.user?.id !== user.id || previous.role !== user.role)
      await clearPrivateQueries(cache)
    checkEpoch(generation)
    useAuthStore.getState().setAuthenticated(user)
    return user
  }
  const refreshInternal = async (generation: number) => {
    const result = sessionSchema.safeParse(await sessionMutation('/auth/refresh'))
    if (!result.success) throw new ApiError(200, 'invalidResponse')
    csrfToken = result.data.csrf_token
    await installUser(result.data.user, generation)
    refreshVersion += 1
  }
  const withFeedback = <T>(action: SessionAction, generation: number, work: () => Promise<T>) => {
    const ticket = ++feedbackTicket
    useFeedback.setState({ pending: true, action, error: null })
    return enqueue(async () => {
      try {
        checkEpoch(generation)
        const value = await work()
        if (ticket === feedbackTicket) useFeedback.setState({ pending: false, error: null })
        return value
      } catch (error) {
        const safe = normalizeApiError(error)
        if (generation === epoch) await clearIdentity()
        if (ticket === feedbackTicket) useFeedback.setState({ pending: false, error: safe })
        throw safe
      }
    })
  }

  const bootstrap = (): Promise<void> => {
    if (bootstrapFlight) return bootstrapFlight
    const generation = ++epoch
    useAuthStore.getState().startLoading()
    const clearing = clearPrivateQueries(cache)
    bootstrapFlight = withFeedback('bootstrap', generation, async () => {
      await clearing
      try {
        await recoverCsrf()
        checkEpoch(generation)
        let user: unknown
        try {
          user = await requestJson('/auth/me')
        } catch (error) {
          if (!(error instanceof ApiError) || error.status !== 401) throw error
          await refreshInternal(generation)
          user = await requestJson('/auth/me') // One refresh and one /me retry only.
        }
        await installUser(user, generation)
      } catch (error) {
        checkEpoch(generation)
        if (!(error instanceof ApiError) || error.status !== 401) throw error
        await clearIdentity()
      }
    }).finally(() => {
      bootstrapFlight = undefined
    })
    return bootstrapFlight
  }
  const refresh = (): Promise<void> => {
    if (refreshFlight) return refreshFlight
    const generation = epoch
    refreshFlight = withFeedback('refresh', generation, () => refreshInternal(generation)).finally(
      () => {
        refreshFlight = undefined
      },
    )
    return refreshFlight
  }
  const login = (credentials: Credentials): Promise<SessionUser> => {
    const generation = ++epoch
    // Hide the previous account immediately; cookie changes wait for older operations to finish.
    useAuthStore.getState().startLoading()
    const clearing = clearPrivateQueries(cache)
    return withFeedback('login', generation, async () => {
      await clearing
      try {
        await recoverCsrf()
      } catch (error) {
        if (!(error instanceof ApiError) || error.status !== 401) throw error
        csrfToken = undefined
      }
      if (csrfToken) {
        await sessionMutation('/auth/logout')
        csrfToken = undefined
      }
      checkEpoch(generation)
      const token = await preauthCsrf()
      const result = sessionSchema.safeParse(
        await requestJson('/auth/login', {
          method: 'POST',
          body: { email: credentials.email.trim(), password: credentials.password },
          csrfToken: token,
        }),
      )
      if (!result.success) throw new ApiError(200, 'invalidResponse')
      csrfToken = result.data.csrf_token
      return installUser(result.data.user, generation)
    })
  }
  const register = (registration: Registration): Promise<void> =>
    enqueue(async () => {
      // Registration does not authenticate; a later session mutation recovers session CSRF.
      const token = await preauthCsrf()
      try {
        const result = registrationSchema.safeParse(
          await requestJson('/auth/register', {
            method: 'POST',
            body: {
              email: registration.email.trim(),
              password: registration.password,
              consent: registration.consent,
            },
            csrfToken: token,
          }),
        )
        if (!result.success) throw new ApiError(201, 'invalidResponse')
      } finally {
        csrfToken = undefined
      }
    })
  const logout = (): Promise<void> => {
    const generation = ++epoch
    useAuthStore.getState().clearSession()
    const clearing = clearPrivateQueries(cache)
    return withFeedback('logout', generation, async () => {
      await clearing
      if (!csrfToken) {
        try {
          await recoverCsrf()
        } catch (error) {
          if (!(error instanceof ApiError) || error.status !== 401) throw error
          await preauthCsrf()
        }
      }
      await sessionMutation('/auth/logout')
      csrfToken = undefined
      checkEpoch(generation)
      await clearIdentity()
    })
  }
  const authenticatedJson = async (
    path: string,
    options: JsonRequestOptions = {},
  ): Promise<unknown> => {
    const generation = epoch
    await queue
    checkEpoch(generation)
    if (useAuthStore.getState().status !== 'authenticated') throw new ApiError(401, 'unauthorized')
    const version = refreshVersion
    const send = () => requestJson(path, { ...options, csrfToken })
    if (options.method && options.method !== 'GET' && !csrfToken) await enqueue(recoverCsrf)
    try {
      const data = await send()
      checkEpoch(generation)
      return data
    } catch (error) {
      checkEpoch(generation)
      if (!(error instanceof ApiError)) throw error
      if (error.status === 403 && options.method && options.method !== 'GET') {
        await enqueue(recoverCsrf)
        checkEpoch(generation)
        const data = await send() // One CSRF recovery/retry, never recursive.
        checkEpoch(generation)
        return data
      }
      if (error.status !== 401) throw error
      if (version === refreshVersion) await refresh()
      checkEpoch(generation)
      try {
        const data = await send()
        checkEpoch(generation)
        return data
      } catch (retryError) {
        if (generation === epoch && retryError instanceof ApiError && retryError.status === 401)
          await clearIdentity()
        throw retryError
      }
    }
  }

  return { bootstrap, refresh, login, register, logout, authenticatedJson, useFeedback }
}

const sessionClient = createSessionClient(queryClient)
export { createSessionClient, sessionClient }
export type { Credentials, Registration }
