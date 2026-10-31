import { CalendarHeart, CheckCircle2, Heart, LoaderCircle, Sprout, UserRound } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { Link } from 'react-router'

import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Typography } from '@/components/ui/typography'
import type { ProfileCompletion } from '@/features/profile/profile-completion'
import { useOwnProfile, useProfileCompletion } from '@/features/profile/queries/use-own-profile'
import { OnboardingIdentityForm } from '@/pages/user/onboarding-identity-page'
import { OnboardingInterestsForm } from '@/pages/user/onboarding-interests-page'
import { OnboardingPreferencesForm } from '@/pages/user/onboarding-preferences-page'

function ProfileReadiness({ completion }: { completion: ProfileCompletion }) {
  const { t } = useTranslation()

  return (
    <Card
      className="rounded-2xl border-border/60 bg-muted/40 shadow-none"
      aria-labelledby="profile-readiness-title"
    >
      <CardHeader>
        <div className="flex items-start gap-3">
          {completion.matching_eligible ? (
            <CheckCircle2 className="mt-0.5 size-5 shrink-0 text-emerald-600" aria-hidden="true" />
          ) : (
            <Sprout className="mt-0.5 size-5 shrink-0 text-primary" aria-hidden="true" />
          )}
          <div className="space-y-1">
            <CardTitle id="profile-readiness-title" className="text-lg">
              {t(
                completion.matching_eligible
                  ? 'profileEdit.matchingReady'
                  : 'profileEdit.matchingDisabled',
              )}
            </CardTitle>
            <CardDescription>
              {t('profileEdit.completionPercentage', { percentage: completion.percentage })}
            </CardDescription>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        <div
          className="h-2 overflow-hidden rounded-full bg-background"
          role="progressbar"
          aria-label={t('userDashboard.completion.label')}
          aria-valuemin={0}
          aria-valuemax={100}
          aria-valuenow={completion.percentage}
        >
          <div
            className="h-full rounded-full bg-primary"
            style={{ width: `${completion.percentage}%` }}
          />
        </div>
      </CardContent>
      {!completion.matching_eligible ? (
        <CardContent className="space-y-3">
          <ul className="space-y-1 text-sm text-muted-foreground">
            {completion.reasons.map((reason) => (
              <li key={reason}>{t(`profileEdit.reasons.${reason}`)}</li>
            ))}
          </ul>
          {completion.missing_fields.length > 0 ? (
            <ul className="flex flex-wrap gap-2" aria-label={t('profileEdit.missingFieldsLabel')}>
              {completion.missing_fields.map((field) => (
                <li
                  key={field}
                  className="rounded-full border border-amber-500/40 bg-amber-500/10 px-3 py-1 text-xs font-semibold"
                >
                  {t(`profileEdit.missingFields.${field}`)}
                </li>
              ))}
            </ul>
          ) : null}
        </CardContent>
      ) : null}
    </Card>
  )
}

function ProfileEditPage() {
  const { t } = useTranslation()
  const profile = useOwnProfile()
  const completion = useProfileCompletion()

  if (profile.isPending) {
    return (
      <section className="flex min-h-72 items-center justify-center gap-3 py-6" aria-busy="true">
        <LoaderCircle
          className="size-5 animate-spin motion-reduce:animate-none"
          aria-hidden="true"
        />
        <span>{t('profileEdit.loading')}</span>
      </section>
    )
  }

  if (profile.isError) {
    return (
      <section className="py-6" aria-labelledby="profile-edit-load-title">
        <Card className="mx-auto max-w-2xl">
          <CardHeader>
            <CardTitle id="profile-edit-load-title">{t('profileEdit.loadErrorTitle')}</CardTitle>
            <CardDescription role="alert">{t('profileEdit.loadError')}</CardDescription>
          </CardHeader>
          <CardContent>
            <Button type="button" onClick={() => void profile.refetch()}>
              {t('profileEdit.retry')}
            </Button>
          </CardContent>
        </Card>
      </section>
    )
  }

  const reloadOwnProfile = async () => {
    const result = await profile.refetch()
    await completion.refetch()
    return result.isError ? undefined : result.data
  }

  return (
    <div className="profile-builder min-w-0 space-y-8 py-2">
      <header className="flex flex-col gap-5 rounded-3xl border border-primary/15 bg-primary/5 p-6 sm:p-8">
        <div className="space-y-2">
          <Typography variant="small" className="font-semibold text-primary">
            {t('profileEdit.eyebrow')}
          </Typography>
          <Typography
            as="h1"
            variant="h3"
            className="max-w-2xl text-balance text-3xl sm:text-4xl"
            id="profile-edit-title"
          >
            {t('profileEdit.title')}
          </Typography>
          <Typography variant="muted" className="max-w-3xl text-base leading-7">
            {t('profileEdit.subtitle')}
          </Typography>
        </div>
        <Button asChild variant="outline" className="w-fit rounded-full">
          <Link to="/user/profile">{t('profileEdit.viewProfile')}</Link>
        </Button>
      </header>

      <nav aria-label={t('profileEdit.sectionNavigation')} className="grid gap-3 sm:grid-cols-3">
        {[
          {
            id: 'profile-edit-identity-title',
            label: 'profileEdit.identityTitle',
            Icon: UserRound,
          },
          {
            id: 'profile-edit-compatibility-title',
            label: 'profileEdit.compatibilityTitle',
            Icon: Heart,
          },
          {
            id: 'profile-edit-preferences-title',
            label: 'profileEdit.preferencesTitle',
            Icon: CalendarHeart,
          },
        ].map(({ id, label, Icon }) => (
          <a
            key={id}
            href={`#${id}`}
            className="flex min-h-14 items-center gap-3 rounded-2xl border border-border/60 bg-card px-4 py-3 text-sm font-semibold transition-colors hover:border-primary/60 hover:bg-primary/5 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary motion-reduce:transition-none"
          >
            <Icon className="size-5 shrink-0 text-primary" aria-hidden="true" />
            {t(label)}
          </a>
        ))}
      </nav>
      <p className="text-sm leading-6 text-muted-foreground">{t('profileEdit.saveHint')}</p>

      <div aria-live="polite" aria-busy={completion.isFetching}>
        {completion.isPending ? (
          <Card>
            <CardContent
              className="flex items-center gap-3 py-6 text-muted-foreground"
              role="status"
            >
              <LoaderCircle
                className="size-5 animate-spin motion-reduce:animate-none"
                aria-hidden="true"
              />
              {t('profileEdit.loadingReadiness')}
            </CardContent>
          </Card>
        ) : completion.isError ? (
          <Card className="border-destructive/40">
            <CardHeader>
              <CardTitle>{t('profileEdit.readinessErrorTitle')}</CardTitle>
              <CardDescription role="alert">{t('profileEdit.readinessError')}</CardDescription>
            </CardHeader>
            <CardContent>
              <Button type="button" variant="outline" onClick={() => void completion.refetch()}>
                {t('profileEdit.retry')}
              </Button>
            </CardContent>
          </Card>
        ) : (
          <ProfileReadiness completion={completion.data} />
        )}
      </div>

      <OnboardingIdentityForm
        initialProfile={profile.data}
        mode="edit"
        onReload={reloadOwnProfile}
      />
      <OnboardingInterestsForm profile={profile.data} mode="edit" onReload={reloadOwnProfile} />
      <OnboardingPreferencesForm profile={profile.data} mode="edit" onReload={reloadOwnProfile} />
    </div>
  )
}

export { ProfileEditPage }
