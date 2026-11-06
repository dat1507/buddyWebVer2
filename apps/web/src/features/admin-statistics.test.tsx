import { QueryClient, QueryClientProvider, focusManager } from '@tanstack/react-query'
import { act, renderHook, cleanup } from '@testing-library/react'
import { afterEach, expect, it, vi } from 'vitest'
import { useAdminUserStatistics } from '@/features/admin-statistics'
import { useAuthStore } from '@/stores/auth-store'
afterEach(() => {
  cleanup()
  focusManager.setFocused(undefined)
  vi.useRealTimers()
  vi.unstubAllGlobals()
  vi.unstubAllEnvs()
  useAuthStore.getState().resetSession()
})
it('polls visible statistics and stops hidden or logged out', async () => {
  vi.useFakeTimers()
  vi.stubEnv('VITE_API_URL', '/api')
  useAuthStore.getState().setAuthenticated({
    id: 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa',
    email: 'admin@example.com',
    role: 'ADMIN',
    email_verified: true,
  })
  const fetch = vi
    .fn()
    .mockImplementation(
      async () =>
        new Response(JSON.stringify({ total_users: 7, observed_at: '2026-11-06T00:00:00Z' })),
    )
  vi.stubGlobal('fetch', fetch)
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  const { unmount } = renderHook(useAdminUserStatistics, {
    wrapper: ({ children }) => (
      <QueryClientProvider client={client}>{children}</QueryClientProvider>
    ),
  })
  await act(async () => {
    await vi.advanceTimersByTimeAsync(10)
  })
  expect(fetch).toHaveBeenCalledTimes(1)
  await act(async () => {
    await vi.advanceTimersByTimeAsync(60000)
  })
  expect(fetch).toHaveBeenCalledTimes(2)
  focusManager.setFocused(false)
  await act(async () => {
    await vi.advanceTimersByTimeAsync(60000)
  })
  expect(fetch).toHaveBeenCalledTimes(2)
  await act(async () => {
    focusManager.setFocused(true)
    await vi.advanceTimersByTimeAsync(10)
  })
  expect(fetch).toHaveBeenCalledTimes(3)
  await act(async () => {
    useAuthStore.getState().clearSession()
    await vi.advanceTimersByTimeAsync(60000)
  })
  expect(fetch).toHaveBeenCalledTimes(3)
  unmount()
  client.clear()
})
