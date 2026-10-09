import { useTranslation } from 'react-i18next'

import { EventsSlider } from '@/components/landing/events-slider'
import { Button } from '@/components/ui/button'
import { Typography } from '@/components/ui/typography'
import { selectLandingEventSliders, type EventSliderLocale } from '@/features/events/event-slider'
import { useEventSliders } from '@/features/events/queries/use-event-sliders'
import type { EventSliderRepository } from '@/features/events/repositories/event-slider-repository'

interface LiveEventsSectionProps {
  locale: EventSliderLocale
  repository?: EventSliderRepository
}

function LiveEventsSection({ locale, repository }: LiveEventsSectionProps) {
  const { t } = useTranslation()
  const events = useEventSliders(locale, repository)

  if (events.isPending) {
    return (
      <section
        className="bg-vgu-surface px-4 py-16 sm:px-6 sm:py-20 lg:px-8"
        aria-labelledby="events-title"
      >
        <div className="mx-auto max-w-4xl space-y-10">
          <Typography id="events-title" variant="h2" className="text-center">
            {t('stats.title')}
          </Typography>
          <div
            role="status"
            aria-label={t('stats.loading')}
            className="aspect-[5/4] animate-pulse rounded-2xl bg-muted motion-reduce:animate-none sm:aspect-[3/2]"
          />
        </div>
      </section>
    )
  }

  if (events.isError) {
    return (
      <section
        className="bg-vgu-surface px-4 py-16 text-center sm:px-6 sm:py-20 lg:px-8"
        aria-labelledby="events-title"
      >
        <div className="mx-auto max-w-3xl space-y-5">
          <Typography id="events-title" variant="h2">
            {t('stats.title')}
          </Typography>
          <p role="alert" className="text-zinc-300">
            {t('stats.error')}
          </p>
          <Button type="button" variant="outline" onClick={() => void events.refetch()}>
            {t('stats.retry')}
          </Button>
        </div>
      </section>
    )
  }

  return <EventsSlider events={selectLandingEventSliders(events.data)} />
}

export { LiveEventsSection }
export type { LiveEventsSectionProps }
