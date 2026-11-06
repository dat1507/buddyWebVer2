import { useQuery } from '@tanstack/react-query'
import { z } from 'zod'
import { requestJson } from '@/lib/api'
import { useAuthStore } from '@/stores/auth-store'

export const statisticsPolling = {
  refetchInterval: 60_000,
  refetchIntervalInBackground: false,
  refetchOnMount: 'always',
  refetchOnWindowFocus: true,
  staleTime: 0,
  meta: { private: true },
} as const

const counts = {
  users: z.object({
    total_users: z.number().int().nonnegative(),
    observed_at: z.string().datetime({ offset: true }),
  }),
  events: z.object({
    published_events: z.number().int().nonnegative(),
    upcoming_events: z.number().int().nonnegative(),
    observed_at: z.string().datetime({ offset: true }),
  }),
}
export function useAdminUserStatistics() {
  const enabled = useAuthStore(
    (state) => state.status === 'authenticated' && state.role === 'ADMIN',
  )
  return useQuery({
    ...statisticsPolling,
    queryKey: ['private', 'admin-users', 'stats'],
    queryFn: async ({ signal }) =>
      counts.users.parse(await requestJson('/admin/users/stats', { signal })),
    enabled,
  })
}
export function useAdminEventStatistics() {
  const enabled = useAuthStore(
    (state) => state.status === 'authenticated' && state.role === 'ADMIN',
  )
  return useQuery({
    ...statisticsPolling,
    queryKey: ['private', 'admin-events', 'stats'],
    queryFn: async ({ signal }) =>
      counts.events.parse(await requestJson('/admin/events/stats', { signal })),
    enabled,
  })
}
