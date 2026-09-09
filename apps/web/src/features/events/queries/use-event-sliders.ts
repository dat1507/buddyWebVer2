import { useQuery } from '@tanstack/react-query'

import type { EventSliderLocale } from '@/features/events/event-slider'
import { eventSliderRepository } from '@/features/events/repositories/event-slider-repository-provider'
import type { EventSliderRepository } from '@/features/events/repositories/event-slider-repository'

const eventSliderQueryKeys = {
  all: ['event-sliders'] as const,
  list: (locale: EventSliderLocale) => [...eventSliderQueryKeys.all, locale] as const,
}

function useEventSliders(
  locale: EventSliderLocale,
  repository: EventSliderRepository = eventSliderRepository,
) {
  return useQuery({
    queryKey: eventSliderQueryKeys.list(locale),
    queryFn: ({ signal }) => repository.listPublished(locale, signal),
    refetchInterval: 60_000,
  })
}

export { eventSliderQueryKeys, useEventSliders }
