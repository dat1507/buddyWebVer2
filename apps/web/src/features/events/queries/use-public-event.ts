import { useQuery } from '@tanstack/react-query'

import { publicEventsClient, type EventLocale } from '@/features/events/public-event'

const publicEventKeys = {
  root: ['events'] as const,
  list: (locale: EventLocale) => [...publicEventKeys.root, 'list', locale] as const,
  detail: (eventId: string, locale: EventLocale) =>
    [...publicEventKeys.root, 'detail', eventId, locale] as const,
}

function usePublicEvents(locale: EventLocale, enabled = true) {
  return useQuery({
    queryKey: publicEventKeys.list(locale),
    queryFn: ({ signal }) => publicEventsClient.readEvents(locale, signal),
    enabled,
  })
}

function usePublicEvent(eventId: string | null, locale: EventLocale) {
  return useQuery({
    queryKey: publicEventKeys.detail(eventId ?? 'none', locale),
    queryFn: ({ signal }) => publicEventsClient.readEvent(eventId!, locale, signal),
    enabled: eventId !== null,
    refetchInterval: (query) => {
      const expiresIn = query.state.data?.cover?.expires_in
      return expiresIn ? Math.max(1_000, Math.floor(expiresIn * 0.8) * 1_000) : false
    },
  })
}

export { publicEventKeys, usePublicEvent, usePublicEvents }
