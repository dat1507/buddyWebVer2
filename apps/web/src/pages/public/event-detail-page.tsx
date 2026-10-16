import { ArrowLeft, Building2, CalendarDays, Clock3, ExternalLink, MapPin, Tag } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { Link, useParams, useSearchParams } from 'react-router'

import { Button } from '@/components/ui/button'
import { Typography } from '@/components/ui/typography'
import type { EventLocale } from '@/features/events/public-event'
import { usePublicEvent } from '@/features/events/queries/use-public-event'
import { ApiError } from '@/lib/api'

const uuidPattern = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i

interface EventDetailBackLink {
  label: string
  to: '/' | '/user/events'
}

function useEventDetailBackLink(): EventDetailBackLink {
  const { t } = useTranslation()
  const [searchParams] = useSearchParams()
  const sources = searchParams.getAll('from')
  return sources.length === 1 && sources[0] === 'user-dashboard'
    ? { label: t('eventDetail.backToEventDashboard'), to: '/user/events' }
    : { label: t('eventDetail.back'), to: '/' }
}

function EventNotFound({ backLink }: { backLink: EventDetailBackLink }) {
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
        <Link to={backLink.to}>{backLink.label}</Link>
      </Button>
    </main>
  )
}

function EventDetailPage() {
  const { t, i18n } = useTranslation()
  const backLink = useEventDetailBackLink()
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
    return <EventNotFound backLink={backLink} />
  }

  if (eventQuery.isPending) {
    return (
      <main className="mx-auto min-h-[60vh] max-w-7xl px-4 py-12 sm:px-6 lg:px-8">
        <div
          role="status"
          className="grid overflow-hidden rounded-[2rem] border border-border bg-card lg:grid-cols-[minmax(0,1.08fr)_minmax(22rem,0.92fr)]"
          aria-label={t('eventDetail.loading')}
        >
          <div className="aspect-[4/5] animate-pulse bg-muted motion-reduce:animate-none lg:aspect-auto lg:min-h-[42rem]" />
          <div className="space-y-6 p-6 sm:p-10">
            <div className="h-7 w-28 animate-pulse rounded-full bg-muted motion-reduce:animate-none" />
            <div className="h-12 w-3/4 animate-pulse rounded bg-muted motion-reduce:animate-none" />
            <div className="h-48 animate-pulse rounded-2xl bg-muted motion-reduce:animate-none" />
            <div className="h-40 animate-pulse rounded-2xl bg-muted motion-reduce:animate-none" />
          </div>
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
  const start = event.start_date ? dateFormatter.format(new Date(event.start_date)) : null
  const end = event.end_date ? dateFormatter.format(new Date(event.end_date)) : null
  const hasDetails = Boolean(
    event.start_date || event.end_date || event.location || event.organizer || event.category,
  )

  return (
    <main className="relative isolate overflow-hidden px-4 py-8 sm:px-6 sm:py-12 lg:px-8">
      <div
        aria-hidden="true"
        className="pointer-events-none absolute inset-x-0 top-0 -z-10 h-80 bg-[radial-gradient(circle_at_top_right,rgba(255,103,13,0.16),transparent_58%)]"
      />
      <div className="mx-auto w-full max-w-7xl">
        <Button asChild variant="link" className="-ml-4 mb-6 gap-2">
          <Link to={backLink.to}>
            <ArrowLeft aria-hidden="true" className="size-4" />
            {backLink.label}
          </Link>
        </Button>

        <article className="grid overflow-hidden rounded-[2rem] border border-border bg-card shadow-2xl lg:grid-cols-[minmax(0,1.08fr)_minmax(22rem,0.92fr)]">
          <figure className="flex min-h-72 items-center justify-center bg-zinc-950 lg:min-h-[42rem]">
            {event.cover ? (
              <img
                src={event.cover.url}
                alt={event.cover.alt_text}
                width={event.cover.width}
                height={event.cover.height}
                className="max-h-[52rem] w-full object-contain"
              />
            ) : (
              <div className="flex min-h-72 size-full items-center justify-center text-zinc-400 lg:min-h-[42rem]">
                {t('eventDetail.noCover')}
              </div>
            )}
          </figure>

          <div className="flex flex-col gap-8 p-6 sm:p-10 lg:p-12">
            <header className="space-y-5">
              <div className="flex flex-wrap gap-2 text-xs font-semibold uppercase tracking-[0.16em]">
                {event.phase ? (
                  <span className="rounded-full border border-vgu-orange/35 bg-vgu-orange/10 px-3 py-1 text-vgu-orange-dark dark:text-vgu-orange">
                    {t(`eventDetail.phase.${event.phase}`)}
                  </span>
                ) : null}
                {event.status === 'CANCELLED' ? (
                  <span className="rounded-full bg-destructive/15 px-3 py-1 text-destructive">
                    {t('eventDetail.cancelled')}
                  </span>
                ) : null}
              </div>
              <Typography
                as="h1"
                variant="h1"
                className="break-words text-4xl font-black uppercase leading-tight tracking-tight sm:text-5xl"
              >
                {event.title}
              </Typography>
            </header>

            <section
              aria-labelledby="event-description-heading"
              className="relative space-y-4 overflow-hidden rounded-2xl border border-border bg-muted/35 p-5 sm:p-6"
            >
              <span aria-hidden="true" className="absolute inset-x-0 top-0 h-1 bg-vgu-orange" />
              <Typography as="h2" id="event-description-heading" variant="h3">
                {t('eventDetail.about')}
              </Typography>
              <p
                data-testid="event-description"
                className="whitespace-pre-wrap break-words text-base leading-8 text-foreground/85"
              >
                {event.description}
              </p>
            </section>

            {event.status === 'CANCELLED' ? (
              <p
                role="status"
                className="rounded-xl border border-destructive/30 bg-destructive/10 p-4"
              >
                {t('eventDetail.cancelledNotice')}
              </p>
            ) : null}

            {event.registration_enabled && event.registration_url ? (
              <section className="space-y-3 rounded-2xl border border-vgu-orange/35 bg-vgu-orange/10 p-5">
                <Typography as="h2" variant="h3">
                  {t('eventDetail.registration.title')}
                </Typography>
                <Typography variant="muted">{t('eventDetail.registration.description')}</Typography>
                <Button asChild className="w-full sm:w-auto">
                  <a href={event.registration_url} target="_blank" rel="noreferrer">
                    <ExternalLink aria-hidden="true" />
                    {t('eventDetail.registration.action')}
                  </a>
                </Button>
              </section>
            ) : null}

            {hasDetails ? (
              <dl className="grid gap-5 rounded-2xl border border-border/70 bg-background/45 p-5 sm:grid-cols-2">
                {event.start_date && start ? (
                  <div className="flex gap-3">
                    <CalendarDays
                      aria-hidden="true"
                      className="mt-0.5 size-5 shrink-0 text-vgu-orange"
                    />
                    <div>
                      <dt className="font-semibold">{t('eventDetail.starts')}</dt>
                      <dd className="text-sm leading-6 text-muted-foreground">
                        <time dateTime={event.start_date}>{start}</time>
                      </dd>
                      {!event.end_date ? (
                        <dd className="text-xs text-muted-foreground">{event.timezone}</dd>
                      ) : null}
                    </div>
                  </div>
                ) : null}
                {event.end_date && end ? (
                  <div className="flex gap-3">
                    <Clock3 aria-hidden="true" className="mt-0.5 size-5 shrink-0 text-vgu-orange" />
                    <div>
                      <dt className="font-semibold">{t('eventDetail.ends')}</dt>
                      <dd className="text-sm leading-6 text-muted-foreground">
                        <time dateTime={event.end_date}>{end}</time>
                      </dd>
                      <dd className="text-xs text-muted-foreground">{event.timezone}</dd>
                    </div>
                  </div>
                ) : null}
                {event.location ? (
                  <div className="flex gap-3 sm:col-span-2">
                    <MapPin aria-hidden="true" className="mt-0.5 size-5 shrink-0 text-vgu-orange" />
                    <div>
                      <dt className="font-semibold">{t('eventDetail.location')}</dt>
                      <dd className="text-sm leading-6 text-muted-foreground">{event.location}</dd>
                    </div>
                  </div>
                ) : null}
                {event.organizer ? (
                  <div className="flex gap-3">
                    <Building2
                      aria-hidden="true"
                      className="mt-0.5 size-5 shrink-0 text-vgu-orange"
                    />
                    <div>
                      <dt className="font-semibold">{t('eventDetail.organizer')}</dt>
                      <dd className="text-sm leading-6 text-muted-foreground">{event.organizer}</dd>
                    </div>
                  </div>
                ) : null}
                {event.category ? (
                  <div className="flex gap-3">
                    <Tag aria-hidden="true" className="mt-0.5 size-5 shrink-0 text-vgu-orange" />
                    <div>
                      <dt className="font-semibold">{t('eventDetail.category')}</dt>
                      <dd className="text-sm leading-6 text-muted-foreground">{event.category}</dd>
                    </div>
                  </div>
                ) : null}
              </dl>
            ) : null}
          </div>
        </article>
      </div>
    </main>
  )
}

export { EventDetailPage }
