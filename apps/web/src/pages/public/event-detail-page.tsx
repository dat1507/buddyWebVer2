import { Building2, CalendarDays, Clock3, MapPin, Tag } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { Link, useParams } from 'react-router'

import { Button } from '@/components/ui/button'
import { Typography } from '@/components/ui/typography'
import type { EventLocale } from '@/features/events/public-event'
import { usePublicEvent } from '@/features/events/queries/use-public-event'
import { ApiError } from '@/lib/api'

const uuidPattern = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i

function EventNotFound() {
  const { t } = useTranslation()
  return (
    <main className="mx-auto flex min-h-[60vh] max-w-3xl flex-col items-center justify-center gap-5 px-4 py-16 text-center">
      <Typography variant="small" className="uppercase tracking-[0.2em] text-vgu-orange">
        404
      </Typography>
      <Typography as="h1" variant="h2">
        {t('eventDetail.notFound.title')}
      </Typography>
      <Typography variant="lead">{t('eventDetail.notFound.description')}</Typography>
      <Button asChild variant="outline">
        <Link to="/">{t('eventDetail.back')}</Link>
      </Button>
    </main>
  )
}

function EventDetailPage() {
  const { t, i18n } = useTranslation()
  const { eventId: routeEventId } = useParams()
  const eventId = routeEventId && uuidPattern.test(routeEventId) ? routeEventId : null
  const locale: EventLocale = i18n.resolvedLanguage?.startsWith('de') ? 'de' : 'en'
  const eventQuery = usePublicEvent(eventId, locale)

  if (
    !eventId ||
    (eventQuery.isError &&
      eventQuery.error instanceof ApiError &&
      eventQuery.error.code === 'notFound')
  ) {
    return <EventNotFound />
  }

  if (eventQuery.isPending) {
    return (
      <main className="mx-auto min-h-[60vh] max-w-6xl px-4 py-12 sm:px-6 lg:px-8">
        <div role="status" className="space-y-5" aria-label={t('eventDetail.loading')}>
          <div className="aspect-[3/2] animate-pulse rounded-3xl bg-muted motion-reduce:animate-none" />
          <div className="h-10 w-3/4 animate-pulse rounded bg-muted motion-reduce:animate-none" />
          <div className="h-24 animate-pulse rounded bg-muted motion-reduce:animate-none" />
        </div>
      </main>
    )
  }

  if (eventQuery.isError) {
    const unauthorized =
      eventQuery.error instanceof ApiError && eventQuery.error.code === 'unauthorized'
    return (
      <main className="mx-auto flex min-h-[60vh] max-w-3xl flex-col items-center justify-center gap-5 px-4 py-16 text-center">
        <Typography as="h1" variant="h2">
          {t(unauthorized ? 'eventDetail.signIn.title' : 'eventDetail.error.title')}
        </Typography>
        <Typography variant="lead">
          {t(unauthorized ? 'eventDetail.signIn.description' : 'eventDetail.error.description')}
        </Typography>
        {unauthorized ? (
          <Button asChild>
            <Link to="/login">{t('eventDetail.signIn.action')}</Link>
          </Button>
        ) : (
          <Button type="button" variant="outline" onClick={() => void eventQuery.refetch()}>
            {t('eventDetail.error.retry')}
          </Button>
        )}
      </main>
    )
  }

  const event = eventQuery.data
  const dateFormatter = new Intl.DateTimeFormat(locale, {
    dateStyle: 'full',
    timeStyle: 'short',
    timeZone: event.timezone,
  })
  const start = dateFormatter.format(new Date(event.start_date))
  const end = dateFormatter.format(new Date(event.end_date))

  return (
    <main className="mx-auto w-full max-w-6xl px-4 py-8 sm:px-6 sm:py-12 lg:px-8">
      <Button asChild variant="link" className="mb-6">
        <Link to="/">{t('eventDetail.back')}</Link>
      </Button>

      <article className="overflow-hidden rounded-3xl border border-border bg-card shadow-xl">
        <div className="aspect-[3/2] w-full bg-muted lg:aspect-[21/9]">
          {event.cover ? (
            <img
              src={event.cover.url}
              alt={event.cover.alt_text}
              width={event.cover.width}
              height={event.cover.height}
              className="size-full object-cover"
            />
          ) : (
            <div className="flex size-full items-center justify-center text-muted-foreground">
              {t('eventDetail.noCover')}
            </div>
          )}
        </div>

        <div className="space-y-8 p-6 sm:p-10">
          <header className="space-y-4">
            <div className="flex flex-wrap gap-2 text-xs font-semibold uppercase tracking-wider">
              <span className="rounded-full bg-vgu-orange/15 px-3 py-1 text-vgu-orange-dark dark:text-vgu-orange">
                {t(`eventDetail.phase.${event.phase}`)}
              </span>
              {event.status === 'CANCELLED' ? (
                <span className="rounded-full bg-destructive/15 px-3 py-1 text-destructive">
                  {t('eventDetail.cancelled')}
                </span>
              ) : null}
            </div>
            <Typography as="h1" variant="h1" className="break-words text-4xl sm:text-5xl">
              {event.title}
            </Typography>
          </header>

          <dl className="grid gap-5 rounded-2xl bg-muted/45 p-5 sm:grid-cols-2">
            <div className="flex gap-3">
              <CalendarDays aria-hidden="true" className="mt-0.5 size-5 shrink-0 text-vgu-orange" />
              <div>
                <dt className="font-semibold">{t('eventDetail.starts')}</dt>
                <dd>
                  <time dateTime={event.start_date}>{start}</time>
                </dd>
              </div>
            </div>
            <div className="flex gap-3">
              <Clock3 aria-hidden="true" className="mt-0.5 size-5 shrink-0 text-vgu-orange" />
              <div>
                <dt className="font-semibold">{t('eventDetail.ends')}</dt>
                <dd>
                  <time dateTime={event.end_date}>{end}</time>
                </dd>
                <dd className="text-sm text-muted-foreground">{event.timezone}</dd>
              </div>
            </div>
            <div className="flex gap-3">
              <MapPin aria-hidden="true" className="mt-0.5 size-5 shrink-0 text-vgu-orange" />
              <div>
                <dt className="font-semibold">{t('eventDetail.location')}</dt>
                <dd>{event.location}</dd>
              </div>
            </div>
            {event.organizer ? (
              <div className="flex gap-3">
                <Building2 aria-hidden="true" className="mt-0.5 size-5 shrink-0 text-vgu-orange" />
                <div>
                  <dt className="font-semibold">{t('eventDetail.organizer')}</dt>
                  <dd>{event.organizer}</dd>
                </div>
              </div>
            ) : null}
            {event.category ? (
              <div className="flex gap-3 sm:col-span-2">
                <Tag aria-hidden="true" className="mt-0.5 size-5 shrink-0 text-vgu-orange" />
                <div>
                  <dt className="font-semibold">{t('eventDetail.category')}</dt>
                  <dd>{event.category}</dd>
                </div>
              </div>
            ) : null}
          </dl>

          {event.status === 'CANCELLED' ? (
            <p
              role="status"
              className="rounded-xl border border-destructive/30 bg-destructive/10 p-4"
            >
              {t('eventDetail.cancelledNotice')}
            </p>
          ) : null}

          <section aria-labelledby="event-description-heading" className="space-y-3">
            <Typography as="h2" id="event-description-heading" variant="h3">
              {t('eventDetail.about')}
            </Typography>
            <p className="whitespace-pre-wrap break-words text-base leading-7 text-muted-foreground">
              {event.description}
            </p>
          </section>
        </div>
      </article>
    </main>
  )
}

export { EventDetailPage }
