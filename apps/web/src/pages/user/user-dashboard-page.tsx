import { useId } from 'react'
import {
  CalendarDays,
  CheckCircle2,
  CircleAlert,
  ExternalLink,
  HeartHandshake,
  LoaderCircle,
  Pencil,
  UserRound,
  type LucideIcon,
} from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { Link } from 'react-router'

import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Typography } from '@/components/ui/typography'
import { UnreadBadge } from '@/components/ui/unread-badge'
import { publicEventsEnabled } from '@/config/launch-scope'
import { useBuddyUnread } from '@/features/chat/buddy-unread-state'
import type { EventLocale, PublicEvent } from '@/features/events/public-event'
import { usePublicEvents } from '@/features/events/queries/use-public-event'
import type { ProfileCompletion } from '@/features/profile/profile-completion'
import type { OwnProfile } from '@/features/profile/profile'
import { useOwnProfile, useProfileCompletion } from '@/features/profile/queries/use-own-profile'

function profileName(profile: OwnProfile, fallback: string): string {
  return profile.display_name?.trim() || profile.full_name?.trim() || fallback
}

function ProfileSummary({ profile }: { profile: OwnProfile }) {
  const { t } = useTranslation()
  const name = profileName(profile, t('profile.unnamed'))
  const studentType = profile.student_type
    ? t(`profile.studentTypes.${profile.student_type}`)
    : t('profile.notAdded')

  return (
    <Card aria-label={t('userDashboard.profileCardLabel', { name })}>
      <CardHeader>
        <div className="flex items-start gap-3">
          <span className="flex size-10 shrink-0 items-center justify-center rounded-full bg-vgu-orange/15 text-vgu-orange-dark">
            <UserRound aria-hidden="true" className="size-5" />
          </span>
          <div className="min-w-0 space-y-1">
            <CardTitle className="break-words">{name}</CardTitle>
            <CardDescription>{studentType}</CardDescription>
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-5">
        <dl className="grid gap-3 sm:grid-cols-2">
          <div className="rounded-xl border border-border/70 bg-background/60 p-3">
            <dt className="text-xs font-semibold uppercase tracking-[0.12em] text-muted-foreground">
              {t('profile.major')}
            </dt>
            <dd className="mt-1 break-words text-sm font-semibold">
              {profile.major?.trim() || t('profile.notAdded')}
            </dd>
          </div>
          <div className="rounded-xl border border-border/70 bg-background/60 p-3">
            <dt className="text-xs font-semibold uppercase tracking-[0.12em] text-muted-foreground">
              {t('profile.studyYear')}
            </dt>
            <dd className="mt-1 text-sm font-semibold">
              {profile.study_year
                ? t('profile.studyYearValue', { year: profile.study_year })
                : t('profile.notAdded')}
            </dd>
          </div>
        </dl>
        <div className="flex flex-wrap gap-3">
          <Button asChild>
            <Link to="/user/profile">
              <UserRound aria-hidden="true" />
              {t('userDashboard.viewProfile')}
            </Link>
          </Button>
          <Button asChild variant="outline">
            <Link to="/user/profile/edit">
              <Pencil aria-hidden="true" />
              {t('userDashboard.editProfile')}
            </Link>
          </Button>
        </div>
      </CardContent>
    </Card>
  )
}

function CompletionSummary({ completion }: { completion: ProfileCompletion }) {
  const { t } = useTranslation()
  const complete = completion.status === 'COMPLETE'

  return (
    <Card className={complete ? 'border-emerald-500/40' : 'border-amber-500/50'}>
      <CardHeader>
        <div className="flex items-start gap-3">
          {complete ? (
            <CheckCircle2 className="mt-0.5 size-5 shrink-0 text-emerald-600" aria-hidden="true" />
          ) : (
            <CircleAlert className="mt-0.5 size-5 shrink-0 text-amber-600" aria-hidden="true" />
          )}
          <div className="space-y-1">
            <CardTitle>
              {t(
                complete
                  ? 'userDashboard.completion.completeTitle'
                  : 'userDashboard.completion.incompleteTitle',
              )}
            </CardTitle>
            <CardDescription>
              {t(
                complete
                  ? 'userDashboard.completion.completeDescription'
                  : 'userDashboard.completion.incompleteDescription',
              )}
            </CardDescription>
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="space-y-2">
          <div className="flex items-center justify-between gap-4 text-sm font-semibold">
            <span>{t('userDashboard.completion.label')}</span>
            <span>
              {t('userDashboard.completion.percentage', { percentage: completion.percentage })}
            </span>
          </div>
          <div
            className="h-2 overflow-hidden rounded-full bg-muted"
            role="progressbar"
            aria-label={t('userDashboard.completion.label')}
            aria-valuemin={0}
            aria-valuemax={100}
            aria-valuenow={completion.percentage}
          >
            <div
              className={complete ? 'h-full bg-emerald-600' : 'h-full bg-amber-500'}
              style={{ width: `${completion.percentage}%` }}
            />
          </div>
        </div>
        {completion.missing_fields.length > 0 ? (
          <div className="space-y-3">
            <Typography variant="small" className="font-semibold">
              {t('profileEdit.missingFieldsLabel')}
            </Typography>
            <ul className="flex flex-wrap gap-2">
              {completion.missing_fields.map((field) => (
                <li
                  key={field}
                  className="rounded-full border border-amber-500/40 bg-amber-500/10 px-3 py-1 text-xs font-semibold"
                >
                  {t(`profileEdit.missingFields.${field}`)}
                </li>
              ))}
            </ul>
            <Button asChild variant="outline">
              <Link to="/user/profile/edit">{t('userDashboard.completion.finishProfile')}</Link>
            </Button>
          </div>
        ) : null}
      </CardContent>
    </Card>
  )
}

function DashboardAction({
  Icon,
  title,
  description,
  action,
  to,
  unreadCount = 0,
}: {
  Icon: LucideIcon
  title: string
  description: string
  action: string
  to: string
  unreadCount?: number
}) {
  const { t } = useTranslation()
  return (
    <Card className="flex min-w-0 flex-col">
      <CardHeader>
        <Icon className="size-6 text-vgu-orange" aria-hidden="true" />
        <div className="flex items-center gap-2">
          <CardTitle>{title}</CardTitle>
          <UnreadBadge
            count={unreadCount}
            label={t('chat.unreadMessages', { count: unreadCount })}
          />
        </div>
        <CardDescription>{description}</CardDescription>
      </CardHeader>
      <CardContent className="mt-auto">
        <Button asChild variant="outline">
          <Link to={to}>{action}</Link>
        </Button>
      </CardContent>
    </Card>
  )
}

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
          <a href={registrationUrl} target="_blank" rel="noreferrer">
            <ExternalLink aria-hidden="true" />
            {t('userDashboard.events.register')}
          </a>
        </Button>
        <Button asChild variant="outline" className="w-full sm:w-auto">
          <Link to={`/user/events/${event.id}`}>
            {t('userDashboard.events.viewDetails')}
          </Link>
        </Button>
      </CardContent>
    </Card>
  )
}

function UserDashboardPage() {
  const { t, i18n } = useTranslation()
  const titleId = useId()
  const profile = useOwnProfile()
  const completion = useProfileCompletion()
  const { summary: unreadSummary } = useBuddyUnread()
  const locale: EventLocale = i18n.resolvedLanguage?.startsWith('de') ? 'de' : 'en'
  const events = usePublicEvents(locale, publicEventsEnabled)

  if (profile.isPending || completion.isPending) {
    return (
      <section className="flex min-h-72 items-center justify-center gap-3 py-6" aria-busy="true">
        <LoaderCircle
          className="size-5 animate-spin motion-reduce:animate-none"
          aria-hidden="true"
        />
        <span role="status">{t('userDashboard.loading')}</span>
      </section>
    )
  }

  if (profile.isError || completion.isError) {
    const retry = () =>
      Promise.all([
        profile.isError ? profile.refetch() : Promise.resolve(),
        completion.isError ? completion.refetch() : Promise.resolve(),
      ])

    return (
      <section className="py-6" aria-labelledby="user-dashboard-error-title">
        <Card className="mx-auto max-w-2xl border-destructive/40">
          <CardHeader>
            <CardTitle id="user-dashboard-error-title">
              {t('userDashboard.loadErrorTitle')}
            </CardTitle>
            <CardDescription role="alert">{t('userDashboard.loadError')}</CardDescription>
          </CardHeader>
          <CardContent>
            <Button type="button" onClick={() => void retry()}>
              {t('userDashboard.retry')}
            </Button>
          </CardContent>
        </Card>
      </section>
    )
  }

  const name = profileName(profile.data, t('profile.unnamed'))
  const matchingAvailable = completion.data.matching_eligible
  const registrationEvents =
    events.data?.items.filter(
      (event) => event.registration_enabled && event.registration_url !== null,
    ) ?? []

  return (
    <section
      aria-labelledby={titleId}
      className="min-w-0 space-y-6 py-6"
      aria-busy={profile.isFetching || completion.isFetching}
    >
      <header className="space-y-2">
        <Typography
          variant="small"
          className="font-semibold uppercase tracking-[0.18em] text-vgu-orange"
        >
          {t('userDashboard.eyebrow')}
        </Typography>
        <Typography as="h1" variant="h2" id={titleId} className="break-words">
          {t('userDashboard.title')}
        </Typography>
        <Typography variant="lead" className="break-words">
          {t('userDashboard.welcome', { name })}
        </Typography>
        <Typography variant="muted" className="max-w-3xl">
          {t('userDashboard.subtitle')}
        </Typography>
      </header>

      <div className="grid min-w-0 gap-4 xl:grid-cols-2">
        <ProfileSummary profile={profile.data} />
        <CompletionSummary completion={completion.data} />
      </div>

      <section className="space-y-4" aria-labelledby="user-dashboard-actions-title">
        <Typography as="h2" variant="h3" id="user-dashboard-actions-title">
          {t('userDashboard.actionsTitle')}
        </Typography>
        <div className="grid min-w-0 gap-4 md:grid-cols-2">
          <DashboardAction
            Icon={HeartHandshake}
            title={t('userDashboard.myBuddy.title')}
            description={t('userDashboard.myBuddy.description')}
            action={t('userDashboard.myBuddy.open')}
            to="/user/buddy"
            unreadCount={unreadSummary.total_unread_messages}
          />
          <DashboardAction
            Icon={HeartHandshake}
            title={t('userDashboard.matching.title')}
            description={t(
              matchingAvailable
                ? 'userDashboard.matching.readyDescription'
                : 'userDashboard.matching.pausedDescription',
            )}
            action={t(
              matchingAvailable
                ? 'userDashboard.matching.open'
                : 'userDashboard.matching.configure',
            )}
            to={matchingAvailable ? '/user/matching' : '/user/profile/edit'}
          />
          {publicEventsEnabled ? (
            <DashboardAction
              Icon={CalendarDays}
              title={t('userDashboard.events.title')}
              description={t('userDashboard.events.description')}
              action={t('userDashboard.events.open')}
              to="/user/events"
            />
          ) : null}
        </div>
      </section>

      {publicEventsEnabled && (events.isPending || events.isError || registrationEvents.length) ? (
        <section className="space-y-4" aria-labelledby="user-dashboard-registration-title">
          <div className="space-y-1">
            <Typography as="h2" variant="h3" id="user-dashboard-registration-title">
              {t('userDashboard.events.registrationTitle')}
            </Typography>
            <Typography variant="muted">
              {t('userDashboard.events.registrationDescription')}
            </Typography>
          </div>
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
          ) : (
            <div className="grid min-w-0 gap-4 md:grid-cols-2">
              {registrationEvents.map((event) => (
                <RegistrationEventCard key={event.id} event={event} locale={locale} />
              ))}
            </div>
          )}
        </section>
      ) : null}
    </section>
  )
}

export { UserDashboardPage }
