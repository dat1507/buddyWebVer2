import { useQuery } from '@tanstack/react-query'

import { publicEventsClient, type EventLocale } from '@/features/events/public-event'
import { useAuthStore } from '@/stores/auth-store'

const publicEventKeys = {
  root: ['events'] as const,
  detail: (eventId: string, locale: EventLocale, viewer: string) =>
    [...publicEventKeys.root, 'detail', eventId, locale, viewer] as const,
}

function usePublicEvent(eventId: string | null, locale: EventLocale) {
  const status = useAuthStore((state) => state.status)
  const viewer = useAuthStore((state) => state.user?.id ?? 'anonymous')

  return useQuery({
    queryKey: publicEventKeys.detail(eventId ?? 'none', locale, viewer),
    queryFn: ({ signal }) => publicEventsClient.readEvent(eventId!, locale, signal),
    // Session bootstrap clears private queries before it establishes the viewer. Starting this
    // query concurrently can leave a direct-link reload on an orphaned loading query. Event
    // visibility is viewer-dependent, so wait for that bootstrap and scope the cache by viewer.
    enabled: eventId !== null && status !== 'unknown' && status !== 'loading',
    meta: { private: true },
    refetchInterval: (query) => {
      const expiresIn = query.state.data?.cover?.expires_in
      return expiresIn ? Math.max(1_000, Math.floor(expiresIn * 0.8) * 1_000) : false
    },
  })
}

export { publicEventKeys, usePublicEvent }
