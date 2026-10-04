import { useId, type ReactNode } from 'react'
import { ArrowLeft, CircleAlert } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { Link, useParams } from 'react-router'

import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Typography } from '@/components/ui/typography'
import type { AdminMatchingParticipantDetail } from '@/features/admin-matching/admin-matching'
import { useAdminMatchingParticipantDetail } from '@/features/admin-matching/queries/use-admin-matching'
import { adminUserDetailSchema, type AdminUserDetail } from '@/features/admin-users/admin-users'
import { useAdminUserDetail } from '@/features/admin-users/queries/use-admin-users'
import type { CatalogLocale } from '@/features/profile/profile-catalog'
import { ApiError } from '@/lib/api'

function catalogLocale(language: string | undefined): CatalogLocale {
  return language?.split('-')[0] === 'de' ? 'de' : 'en'
}

function formatDateTime(value: string, language: string): string {
  return new Intl.DateTimeFormat(language, { dateStyle: 'medium', timeZone: 'UTC' }).format(
    new Date(value),
  )
}

function formatDate(value: string, language: string): string {
  return formatDateTime(`${value}T00:00:00Z`, language)
}

function displayName(detail: AdminUserDetail, unavailable: string): string {
  return (
    detail.profile?.display_name?.trim() ||
    detail.profile?.full_name?.trim() ||
    detail.email.trim() ||
    unavailable
  )
}

function StatusBadge({ positive, label }: { positive: boolean; label: string }) {
  return (
    <span
      className={
        positive
          ? 'inline-flex max-w-full rounded-full bg-emerald-500/10 px-2 py-1 text-xs font-semibold text-emerald-700 dark:text-emerald-300'
          : 'inline-flex max-w-full rounded-full bg-muted px-2 py-1 text-xs font-semibold text-muted-foreground'
      }
    >
      <span className="break-words">{label}</span>
    </span>
  )
}

function DetailValue({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="min-w-0 space-y-1 rounded-lg border p-3">
      <dt className="text-sm text-muted-foreground break-words">{label}</dt>
      <dd className="min-w-0 break-words">{children}</dd>
    </div>
  )
}

function AccountCard({ detail, language }: { detail: AdminUserDetail; language: string }) {
  const { t } = useTranslation()
  const headingId = useId()

  return (
    <Card className="min-w-0 shadow-none" aria-labelledby={headingId}>
      <CardHeader>
        <CardTitle id={headingId} className="break-words">
          {t('adminUserDetail.account.title')}
        </CardTitle>
      </CardHeader>
      <CardContent>
        <dl className="grid min-w-0 gap-3 sm:grid-cols-2">
          <DetailValue label={t('adminUserDetail.account.email')}>
            <span className="break-all">{detail.email}</span>
          </DetailValue>
          <DetailValue label={t('adminUserDetail.account.role')}>
            {t('adminUserDetail.account.student')}
          </DetailValue>
          <DetailValue label={t('adminUserDetail.account.status')}>
            <StatusBadge
              positive={detail.is_active}
              label={t(
                detail.is_active
                  ? 'adminUserDetail.status.active'
                  : 'adminUserDetail.status.inactive',
              )}
            />
          </DetailValue>
          <DetailValue label={t('adminUserDetail.account.verification')}>
            <StatusBadge
              positive={detail.email_verified}
              label={t(
                detail.email_verified
                  ? 'adminUserDetail.status.verified'
                  : 'adminUserDetail.status.unverified',
              )}
            />
          </DetailValue>
          <DetailValue label={t('adminUserDetail.account.created')}>
            {formatDateTime(detail.created_at, language)}
          </DetailValue>
        </dl>
      </CardContent>
    </Card>
  )
}

function ProfileCard({ detail, language }: { detail: AdminUserDetail; language: string }) {
  const { t } = useTranslation()
  const headingId = useId()
  const profile = detail.profile
  const unavailable = t('adminUserDetail.unavailable')
  const stay =
    profile?.arrival_date || profile?.departure_date
      ? t('adminUserDetail.profile.stayValue', {
          arrival: profile.arrival_date ? formatDate(profile.arrival_date, language) : unavailable,
          departure: profile.departure_date
            ? formatDate(profile.departure_date, language)
            : unavailable,
        })
      : unavailable

  return (
    <Card className="min-w-0 shadow-none" aria-labelledby={headingId}>
      <CardHeader>
        <CardTitle id={headingId} className="break-words">
          {t('adminUserDetail.profile.title')}
        </CardTitle>
      </CardHeader>
      <CardContent>
        {!profile ? (
          <p role="status" className="text-muted-foreground">
            {t('adminUserDetail.profile.missing')}
          </p>
        ) : (
          <dl className="grid min-w-0 gap-3 sm:grid-cols-2">
            <DetailValue label={t('adminUserDetail.profile.fullName')}>
              {profile.full_name?.trim() || unavailable}
            </DetailValue>
            <DetailValue label={t('adminUserDetail.profile.displayName')}>
              {profile.display_name?.trim() || unavailable}
            </DetailValue>
            <DetailValue label={t('adminUserDetail.profile.studentType')}>
              {profile.student_type
                ? t(`adminUsers.studentTypes.${profile.student_type}`)
                : unavailable}
            </DetailValue>
            <DetailValue label={t('adminUserDetail.profile.nationality')}>
              {profile.nationality?.trim() || unavailable}
            </DetailValue>
            <DetailValue label={t('adminUserDetail.profile.major')}>
              {profile.major?.trim() || unavailable}
            </DetailValue>
            <DetailValue label={t('adminUserDetail.profile.studyYear')}>
              {profile.study_year ?? unavailable}
            </DetailValue>
            <DetailValue label={t('adminUserDetail.profile.homeUniversity')}>
              {profile.home_university?.trim() || unavailable}
            </DetailValue>
            <DetailValue label={t('adminUserDetail.profile.stay')}>{stay}</DetailValue>
            <DetailValue label={t('adminUserDetail.profile.avatar')}>
              {t(
                profile.avatar
                  ? 'adminUserDetail.status.available'
                  : 'adminUserDetail.status.unavailable',
              )}
            </DetailValue>
            <DetailValue label={t('adminUserDetail.profile.bio')}>
              {profile.bio?.trim() || unavailable}
            </DetailValue>
          </dl>
        )}
      </CardContent>
    </Card>
  )
}

function MatchingCard({ detail }: { detail: AdminMatchingParticipantDetail | null }) {
  const { t } = useTranslation()
  const headingId = useId()

  return (
    <Card className="min-w-0 shadow-none" aria-labelledby={headingId}>
      <CardHeader>
        <CardTitle id={headingId} className="break-words">
          {t('adminUserDetail.matching.title')}
        </CardTitle>
      </CardHeader>
      <CardContent>
        {!detail ? (
          <p role="status" className="text-muted-foreground">
            {t('adminUserDetail.matching.unavailable')}
          </p>
        ) : (
          <dl className="grid min-w-0 gap-3 sm:grid-cols-2">
            <DetailValue label={t('adminUserDetail.matching.optIn')}>
              <StatusBadge
                positive={detail.matching_opt_in}
                label={t(
                  detail.matching_opt_in
                    ? 'adminUserDetail.status.yes'
                    : 'adminUserDetail.status.no',
                )}
              />
            </DetailValue>
            <DetailValue label={t('adminUserDetail.matching.buddies')}>
              <span className="text-lg font-semibold tabular-nums">{detail.buddy_count}</span>
            </DetailValue>
            <DetailValue label={t('adminUserDetail.matching.status')}>
              <StatusBadge
                positive={detail.buddy_count > 0}
                label={t(
                  detail.buddy_count > 0
                    ? 'adminUserDetail.matching.hasBuddies'
                    : 'adminUserDetail.matching.noBuddies',
                )}
              />
            </DetailValue>
          </dl>
        )}
      </CardContent>
    </Card>
  )
}

function ActivityCard({
  detail,
  matching,
  language,
}: {
  detail: AdminUserDetail
  matching: AdminMatchingParticipantDetail | null
  language: string
}) {
  const { t } = useTranslation()
  const headingId = useId()
  const activities = matching?.profile.activities ?? []
  const onboarding = detail.profile?.onboarding_completed_at

  return (
    <Card className="min-w-0 shadow-none" aria-labelledby={headingId}>
      <CardHeader>
        <CardTitle id={headingId} className="break-words">
          {t('adminUserDetail.activity.title')}
        </CardTitle>
      </CardHeader>
      <CardContent className="min-w-0 space-y-4">
        <dl className="grid min-w-0 gap-3 sm:grid-cols-2">
          <DetailValue label={t('adminUserDetail.activity.accountCreated')}>
            {formatDateTime(detail.created_at, language)}
          </DetailValue>
          <DetailValue label={t('adminUserDetail.activity.onboardingCompleted')}>
            {onboarding
              ? formatDateTime(onboarding, language)
              : t('adminUserDetail.activity.notCompleted')}
          </DetailValue>
        </dl>
        <div className="min-w-0 space-y-2">
          <Typography variant="small" className="font-semibold">
            {t('adminUserDetail.activity.preferences')}
          </Typography>
          {activities.length > 0 ? (
            <ul
              className="flex min-w-0 flex-wrap gap-2"
              aria-label={t('adminUserDetail.activity.preferences')}
            >
              {activities.map((activity) => (
                <li
                  key={activity.id ?? activity.code ?? activity.label}
                  className="max-w-full break-words rounded-full border bg-background px-3 py-1 text-xs font-medium"
                >
                  {activity.label}
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-sm text-muted-foreground">
              {t(
                detail.profile
                  ? 'adminUserDetail.activity.none'
                  : 'adminUserDetail.activity.unavailable',
              )}
            </p>
          )}
        </div>
      </CardContent>
    </Card>
  )
}

function AdminUserDetailPage() {
  const { t, i18n } = useTranslation()
  const titleId = useId()
  const rawUserId = useParams<{ userId: string }>().userId ?? ''
  const userId = adminUserDetailSchema.shape.id.safeParse(rawUserId).success ? rawUserId : null
  const user = useAdminUserDetail(userId)
  const profileId = user.data?.profile?.id ?? null
  const locale = catalogLocale(i18n.resolvedLanguage)
  const matching = useAdminMatchingParticipantDetail({ profileId, locale })
  const language = i18n.resolvedLanguage ?? 'en'
  const notFound =
    userId === null || (user.error instanceof ApiError && user.error.code === 'notFound')
  const matchingMismatch = Boolean(
    profileId && matching.data && matching.data.profile.id !== profileId,
  )
  const loading = userId !== null && (user.isPending || Boolean(profileId && matching.isPending))
  const failed = user.isError || Boolean(profileId && matching.isError) || matchingMismatch
  const detail = user.data
  const safeMatching = profileId && matching.data?.profile.id === profileId ? matching.data : null
  const title = detail
    ? displayName(detail, t('adminUserDetail.unavailable'))
    : t('adminUserDetail.title')

  const retry = () => {
    if (user.isError) void user.refetch()
    else if (profileId) void matching.refetch()
  }

  return (
    <section
      data-testid="admin-user-detail"
      aria-labelledby={titleId}
      aria-busy={loading}
      className="min-w-0 space-y-6 py-6"
    >
      <Button asChild variant="outline" size="sm">
        <Link to="/admin/users">
          <ArrowLeft aria-hidden="true" />
          {t('adminUserDetail.back')}
        </Link>
      </Button>

      <header className="min-w-0 space-y-2">
        <Typography as="h1" variant="h2" id={titleId} className="break-words text-3xl sm:text-4xl">
          {title}
        </Typography>
        <Typography variant="lead" className="max-w-3xl break-words">
          {t('adminUserDetail.description')}
        </Typography>
        {detail ? <p className="break-all text-sm text-muted-foreground">{detail.email}</p> : null}
        <p className="flex items-start gap-2 text-sm text-muted-foreground">
          <CircleAlert aria-hidden="true" className="mt-0.5 size-4 shrink-0" />
          <span className="break-words">{t('adminUserDetail.readOnly')}</span>
        </p>
      </header>

      {notFound ? (
        <Card className="min-w-0 p-6 shadow-none">
          <Typography as="h2" variant="h3" className="break-words">
            {t('adminUserDetail.notFound.title')}
          </Typography>
          <p className="mt-2 text-muted-foreground">{t('adminUserDetail.notFound.description')}</p>
        </Card>
      ) : loading ? (
        <Card className="min-w-0 p-6 shadow-none">
          <p role="status">{t('adminUserDetail.loading')}</p>
        </Card>
      ) : failed || !detail ? (
        <Card className="min-w-0 border-destructive/40 p-6 shadow-none">
          <div className="space-y-3">
            <p role="alert">{t('adminUserDetail.error')}</p>
            <Button type="button" variant="outline" onClick={retry}>
              {t('adminUserDetail.retry')}
            </Button>
          </div>
        </Card>
      ) : (
        <div className="grid min-w-0 gap-4 xl:grid-cols-2">
          <AccountCard detail={detail} language={language} />
          <ProfileCard detail={detail} language={language} />
          <MatchingCard detail={safeMatching} />
          <ActivityCard detail={detail} matching={safeMatching} language={language} />
        </div>
      )}
    </section>
  )
}

export { AdminUserDetailPage }
