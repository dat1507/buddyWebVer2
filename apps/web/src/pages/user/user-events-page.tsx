import { useId } from 'react'
import { ExternalLink } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { Link } from 'react-router'

import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Typography } from '@/components/ui/typography'
import type { EventLocale, PublicEvent } from '@/features/events/public-event'
import { usePublicEvents } from '@/features/events/queries/use-public-event'

function RegistrationEventCard({ event, locale }: { event: PublicEvent; locale: EventLocale }) {
  const { t } = useTranslation()
  const registrationUrl = event.registration_url
  if (!event.registration_enabled || !registrationUrl) return null
  const start = event.start_date
    ? new Intl.DateTimeFormat(locale, {
        dateStyle: 'medium',
        timeStyle: 'short',
        timeZone: event.timezone,
      }).format(new Date(event.start_date))
    : null

  return (
    <Card className="flex min-w-0 flex-col">
      <CardHeader>
        <CardTitle className="break-words">{event.title}</CardTitle>
        {start || event.location ? (
          <CardDescription className="space-y-1">
            {start ? <span className="block">{start}</span> : null}
            {event.location ? <span className="block">{event.location}</span> : null}
          </CardDescription>
        ) : null}
      </CardHeader>
      <CardContent className="mt-auto flex flex-col gap-3 sm:flex-row sm:flex-wrap">
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
        <Button asChild variant="outline" className="w-full sm:w-auto">
          <Link
            to={`/events/${event.id}?from=user-dashboard`}
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
  const locale: EventLocale = i18n.resolvedLanguage?.startsWith('de') ? 'de' : 'en'
  const events = usePublicEvents(locale)
  const registrationEvents =
    events.data?.items.filter(
      (event) => event.registration_enabled && event.registration_url !== null,
    ) ?? []

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
      ) : registrationEvents.length ? (
        <div className="grid min-w-0 gap-4 md:grid-cols-2">
          {registrationEvents.map((event) => (
            <RegistrationEventCard key={event.id} event={event} locale={locale} />
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
