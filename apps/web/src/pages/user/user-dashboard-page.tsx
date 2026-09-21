import { useId } from 'react'
import {
  CalendarDays,
  CheckCircle2,
  CircleAlert,
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
}: {
  Icon: LucideIcon
  title: string
  description: string
  action: string
  to: string
}) {
  return (
    <Card className="flex min-w-0 flex-col">
      <CardHeader>
        <Icon className="size-6 text-vgu-orange" aria-hidden="true" />
        <CardTitle>{title}</CardTitle>
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

function UserDashboardPage() {
  const { t } = useTranslation()
  const titleId = useId()
  const profile = useOwnProfile()
  const completion = useProfileCompletion()

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
          <DashboardAction
            Icon={CalendarDays}
            title={t('userDashboard.events.title')}
            description={t('userDashboard.events.description')}
            action={t('userDashboard.events.open')}
            to="/user/events"
          />
        </div>
      </section>
    </section>
  )
}

export { UserDashboardPage }
