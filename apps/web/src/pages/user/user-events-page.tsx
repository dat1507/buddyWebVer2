import { useId } from 'react'
import { ExternalLink } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { Link } from 'react-router'

import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Typography } from '@/components/ui/typography'
import {
  selectLandingEventSliders,
  type EventSlider,
  type EventSliderLocale,
} from '@/features/events/event-slider'
import { useEventSliders } from '@/features/events/queries/use-event-sliders'

function EventDashboardCard({ event, locale }: { event: EventSlider; locale: EventSliderLocale }) {
  const { t } = useTranslation()
  const registrationUrl = event.registrationEnabled ? event.registrationUrl?.trim() || null : null
  const start = event.eventStartAt
    ? new Intl.DateTimeFormat(locale, {
        dateStyle: 'medium',
        timeStyle: 'short',
      }).format(new Date(event.eventStartAt))
    : null
  const detailHref = event.cta?.href ?? `/events/${event.id}`

  return (
    <Card className="flex min-w-0 flex-col overflow-hidden">
      <div className="flex aspect-[16/9] items-center justify-center bg-zinc-950">
        <img
          src={event.imageUrl}
          alt={event.imageAlt}
          className="size-full object-contain"
          loading="lazy"
          decoding="async"
        />
      </div>
      <CardHeader>
        <CardTitle className="break-words">{event.title}</CardTitle>
        {event.description ? (
          <p className="line-clamp-3 whitespace-pre-wrap break-words text-sm leading-6 text-foreground/80">
            {event.description}
          </p>
        ) : null}
        {start || event.location ? (
          <CardDescription className="space-y-1">
            {start ? <span className="block">{start}</span> : null}
            {event.location ? <span className="block">{event.location}</span> : null}
          </CardDescription>
        ) : null}
      </CardHeader>
      <CardContent className="mt-auto flex flex-col gap-3 sm:flex-row sm:flex-wrap">
        {registrationUrl ? (
          <Button asChild className="w-full sm:w-auto">
            <a
              href={registrationUrl}
              target="_blank"
              rel="noreferrer"
              aria-label={t('userDashboard.events.registerLabel', { title: event.title })}
            >
              <ExternalLink aria-hidden="true" />
              {t('userDashboard.events.register')}
            </a>
          </Button>
        ) : null}
        <Button
          asChild
          variant={registrationUrl ? 'outline' : 'default'}
          className="w-full sm:w-auto"
        >
          <Link
            to={`${detailHref}?from=user-dashboard`}
            aria-label={t('userDashboard.events.viewDetailsLabel', { title: event.title })}
          >
            {t('userDashboard.events.viewDetails')}
          </Link>
        </Button>
      </CardContent>
    </Card>
  )
}

function UserEventsPage() {
  const { t, i18n } = useTranslation()
  const titleId = useId()
  const locale: EventSliderLocale = i18n.resolvedLanguage?.startsWith('de') ? 'de' : 'en'
  const events = useEventSliders(locale)
  const visibleEvents = selectLandingEventSliders(events.data ?? [])

  return (
    <section
      aria-labelledby={titleId}
      className="min-w-0 space-y-6 py-6"
      aria-busy={events.isFetching}
    >
      <header className="space-y-2">
        <Typography as="h1" variant="h2" id={titleId} className="break-words">
          {t('userDashboard.events.title')}
        </Typography>
        <Typography variant="lead" className="max-w-3xl break-words">
          {t('userDashboard.events.registrationDescription')}
        </Typography>
      </header>

      {events.isPending ? (
        <p role="status" className="text-sm text-muted-foreground">
          {t('userDashboard.events.loading')}
        </p>
      ) : events.isError ? (
        <Card className="border-destructive/40">
          <CardContent className="flex flex-col items-start gap-3 pt-6">
            <p role="alert" className="text-sm text-destructive">
              {t('userDashboard.events.loadError')}
            </p>
            <Button type="button" variant="outline" onClick={() => void events.refetch()}>
              {t('userDashboard.retry')}
            </Button>
          </CardContent>
        </Card>
      ) : visibleEvents.length ? (
        <div className="grid min-w-0 gap-4 md:grid-cols-2">
          {visibleEvents.map((event) => (
            <EventDashboardCard key={event.id} event={event} locale={locale} />
          ))}
        </div>
      ) : (
        <Card>
          <CardHeader>
            <CardTitle>{t('userDashboard.events.emptyTitle')}</CardTitle>
            <CardDescription>{t('userDashboard.events.emptyDescription')}</CardDescription>
          </CardHeader>
        </Card>
      )}
    </section>
  )
}

export { UserEventsPage }
