import { GraduationCap, Languages, LoaderCircle, MapPin, Pencil, Sparkles } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { Link } from 'react-router'

import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Typography } from '@/components/ui/typography'
import { EmailVerificationStatus } from '@/features/auth/email-verification-status'
import type { CatalogLocale } from '@/features/profile/profile-catalog'
import type { OwnProfile } from '@/features/profile/profile'
import {
  useInterestCatalog,
  useLanguageCatalog,
} from '@/features/profile/queries/use-profile-catalogs'
import { useOwnProfile } from '@/features/profile/queries/use-own-profile'
import { useProfilePhotoUrl } from '@/features/profile/queries/use-profile-photo-url'

function catalogLocale(language: string | undefined): CatalogLocale {
  return language?.split('-')[0] === 'de' ? 'de' : 'en'
}

function displayName(profile: OwnProfile, fallback: string): string {
  return profile.display_name?.trim() || profile.full_name?.trim() || fallback
}

function initials(name: string): string {
  const parts = name.trim().split(/\s+/).filter(Boolean)
  if (parts.length === 0) return 'VB'
  return parts
    .slice(0, 2)
    .map((part) => part[0]?.toLocaleUpperCase() ?? '')
    .join('')
}

function ProfileAvatar({ profile, name }: { profile: OwnProfile; name: string }) {
  const { t } = useTranslation()
  const avatarId = profile.avatar?.processing_status === 'READY' ? profile.avatar.id : null
  const photoUrl = useProfilePhotoUrl(avatarId)

  return (
    <div className="space-y-2">
      <div className="relative flex size-32 items-center justify-center overflow-hidden rounded-full border-4 border-card bg-gradient-to-br from-vgu-orange to-vgu-orange-dark text-3xl font-black text-vgu-black shadow-xl">
        {photoUrl.data ? (
          <img
            src={photoUrl.data.url}
            alt={t('profile.avatarAlt', { name })}
            className="size-full object-cover"
            referrerPolicy="no-referrer"
            onError={() => void photoUrl.refetch()}
          />
        ) : (
          <span aria-hidden="true">{initials(name)}</span>
        )}
        {photoUrl.isFetching && avatarId ? (
          <span
            className="absolute inset-0 flex items-center justify-center bg-black/35 text-white"
            role="status"
            aria-label={t('profile.loadingAvatar')}
          >
            <LoaderCircle
              className="size-6 animate-spin motion-reduce:animate-none"
              aria-hidden="true"
            />
          </span>
        ) : null}
      </div>
      {photoUrl.isError ? (
        <div className="space-y-1 text-center">
          <p className="text-xs text-destructive" role="alert">
            {t('profile.avatarError')}
          </p>
          <Button type="button" size="sm" variant="ghost" onClick={() => void photoUrl.refetch()}>
            {t('profile.retryAvatar')}
          </Button>
        </div>
      ) : null}
    </div>
  )
}

function ProfileDetail({ label, value }: { label: string; value: string | null }) {
  const { t } = useTranslation()
  return (
    <div className="space-y-1 rounded-xl border border-border/70 bg-background/60 p-4">
      <dt className="text-xs font-semibold uppercase tracking-[0.12em] text-muted-foreground">
        {label}
      </dt>
      <dd className="text-sm font-semibold text-foreground">{value || t('profile.notAdded')}</dd>
    </div>
  )
}

function InterestList({ profile, locale }: { profile: OwnProfile; locale: CatalogLocale }) {
  const { t } = useTranslation()
  const catalog = useInterestCatalog(locale)

  if (catalog.isPending) {
    return <p role="status">{t('profile.loadingInterests')}</p>
  }
  if (catalog.isError) {
    return (
      <div className="space-y-3">
        <p className="text-sm text-destructive" role="alert">
          {t('profile.interestsError')}
        </p>
        <Button type="button" size="sm" variant="outline" onClick={() => void catalog.refetch()}>
          {t('profile.retry')}
        </Button>
      </div>
    )
  }
  if (profile.interest_ids.length === 0) {
    return <p className="text-sm text-muted-foreground">{t('profile.noInterests')}</p>
  }

  const labels = new Map(catalog.data.items.map((item) => [item.id, item.label]))
  return (
    <ul className="flex flex-wrap gap-2" aria-label={t('profile.interestsLabel')}>
      {profile.interest_ids.map((interestId) => (
        <li
          key={interestId}
          className="rounded-full border border-vgu-orange/30 bg-vgu-orange/10 px-3 py-1.5 text-sm font-medium"
        >
          {labels.get(interestId) ?? t('profile.unavailableInterest')}
        </li>
      ))}
    </ul>
  )
}

function LanguageList({ profile, locale }: { profile: OwnProfile; locale: CatalogLocale }) {
  const { t } = useTranslation()
  const catalog = useLanguageCatalog(locale)

  if (catalog.isPending) {
    return <p role="status">{t('profile.loadingLanguages')}</p>
  }
  if (catalog.isError) {
    return (
      <div className="space-y-3">
        <p className="text-sm text-destructive" role="alert">
          {t('profile.languagesError')}
        </p>
        <Button type="button" size="sm" variant="outline" onClick={() => void catalog.refetch()}>
          {t('profile.retry')}
        </Button>
      </div>
    )
  }
  if (profile.languages.length === 0) {
    return <p className="text-sm text-muted-foreground">{t('profile.noLanguages')}</p>
  }

  const labels = new Map(catalog.data.items.map((item) => [item.code, item.label]))
  return (
    <ul className="grid gap-3 sm:grid-cols-2" aria-label={t('profile.languagesLabel')}>
      {profile.languages.map(({ language_code, proficiency }) => (
        <li
          key={language_code}
          className="flex items-center justify-between gap-3 rounded-xl border border-border/70 bg-background/60 p-3"
        >
          <span className="font-semibold">
            {labels.get(language_code) ?? language_code.toUpperCase()}
          </span>
          <span className="rounded-full bg-muted px-2.5 py-1 text-xs font-medium text-muted-foreground">
            {t(`onboarding.compatibility.proficiencies.${proficiency}`)}
          </span>
        </li>
      ))}
    </ul>
  )
}

function ProfileView({ profile }: { profile: OwnProfile }) {
  const { t, i18n } = useTranslation()
  const locale = catalogLocale(i18n.resolvedLanguage)
  const name = displayName(profile, t('profile.unnamed'))
  const fullName = profile.full_name?.trim() || null
  const studentType = profile.student_type
    ? t(`profile.studentTypes.${profile.student_type}`)
    : null

  return (
    <section className="min-w-0 space-y-6 py-6" aria-labelledby="profile-title">
      <header className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div className="space-y-2">
          <Typography
            variant="small"
            className="font-semibold uppercase tracking-[0.18em] text-vgu-orange"
          >
            {t('profile.eyebrow')}
          </Typography>
          <Typography as="h1" variant="h2" id="profile-title">
            {t('profile.title')}
          </Typography>
          <Typography variant="muted" className="max-w-2xl text-base leading-7">
            {t('profile.subtitle')}
          </Typography>
        </div>
        <Button asChild>
          <Link to="/user/profile/edit">
            <Pencil aria-hidden="true" />
            {t('profile.edit')}
          </Link>
        </Button>
      </header>

      <EmailVerificationStatus manage />

      <Card className="overflow-hidden" aria-label={t('profile.cardLabel', { name })}>
        <div className="h-36 bg-gradient-to-br from-zinc-950 via-zinc-900 to-vgu-orange/80" />
        <CardContent className="relative space-y-8 px-5 pb-8 pt-20 sm:px-8">
          <div className="absolute -top-16 left-5 sm:left-8">
            <ProfileAvatar profile={profile} name={name} />
          </div>

          <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
            <div className="min-w-0">
              <h2 className="break-words text-3xl font-black tracking-tight">{name}</h2>
              {fullName && fullName !== name ? (
                <p className="mt-1 text-sm text-muted-foreground">
                  {t('profile.fullName', { name: fullName })}
                </p>
              ) : null}
            </div>
            {studentType ? (
              <span className="w-fit rounded-full border border-vgu-orange/40 bg-vgu-orange/10 px-3 py-1.5 text-sm font-semibold text-vgu-orange-dark dark:text-vgu-orange">
                {studentType}
              </span>
            ) : null}
          </div>

          <div className="grid gap-6 lg:grid-cols-[minmax(0,1.2fr)_minmax(18rem,0.8fr)]">
            <div className="space-y-6">
              <section className="space-y-3" aria-labelledby="profile-about-title">
                <div className="flex items-center gap-2">
                  <Sparkles className="size-5 text-vgu-orange" aria-hidden="true" />
                  <h3 id="profile-about-title" className="text-xl font-bold">
                    {t('profile.aboutTitle')}
                  </h3>
                </div>
                <p className="whitespace-pre-wrap text-sm leading-7 text-muted-foreground">
                  {profile.bio?.trim() || t('profile.noBio')}
                </p>
              </section>

              <section className="space-y-3" aria-labelledby="profile-interests-title">
                <div className="flex items-center justify-between gap-3">
                  <div className="flex items-center gap-2">
                    <Sparkles className="size-5 text-vgu-orange" aria-hidden="true" />
                    <h3 id="profile-interests-title" className="text-xl font-bold">
                      {t('profile.interestsTitle')}
                    </h3>
                  </div>
                  <Button asChild variant="ghost" size="sm">
                    <Link to="/user/profile/edit">{t('profile.editInterests')}</Link>
                  </Button>
                </div>
                <InterestList profile={profile} locale={locale} />
              </section>

              <section className="space-y-3" aria-labelledby="profile-languages-title">
                <div className="flex items-center gap-2">
                  <Languages className="size-5 text-vgu-orange" aria-hidden="true" />
                  <h3 id="profile-languages-title" className="text-xl font-bold">
                    {t('profile.languagesTitle')}
                  </h3>
                </div>
                <LanguageList profile={profile} locale={locale} />
              </section>
            </div>

            <aside className="space-y-4" aria-labelledby="profile-details-title">
              <div className="flex items-center gap-2">
                <GraduationCap className="size-5 text-vgu-orange" aria-hidden="true" />
                <h3 id="profile-details-title" className="text-xl font-bold">
                  {t('profile.detailsTitle')}
                </h3>
              </div>
              <dl className="grid gap-3">
                <ProfileDetail label={t('profile.major')} value={profile.major?.trim() || null} />
                <ProfileDetail
                  label={t('profile.studyYear')}
                  value={
                    profile.study_year
                      ? t('profile.studyYearValue', { year: profile.study_year })
                      : null
                  }
                />
                <ProfileDetail
                  label={t('profile.nationality')}
                  value={profile.nationality?.trim() || null}
                />
              </dl>
              <div className="flex items-start gap-2 rounded-xl bg-muted/60 p-4 text-sm leading-6 text-muted-foreground">
                <MapPin className="mt-0.5 size-4 shrink-0" aria-hidden="true" />
                <p>{t('profile.privateNote')}</p>
              </div>
            </aside>
          </div>
        </CardContent>
      </Card>
    </section>
  )
}

function ProfilePage() {
  const { t } = useTranslation()
  const profile = useOwnProfile()

  if (profile.isPending) {
    return (
      <section className="flex min-h-72 items-center justify-center py-6" aria-busy="true">
        <div className="flex items-center gap-3 text-muted-foreground" role="status">
          <LoaderCircle
            className="size-5 animate-spin motion-reduce:animate-none"
            aria-hidden="true"
          />
          <span>{t('profile.loading')}</span>
        </div>
      </section>
    )
  }

  if (profile.isError) {
    return (
      <section className="py-6" aria-labelledby="profile-load-title">
        <Card className="mx-auto max-w-2xl">
          <CardHeader>
            <CardTitle id="profile-load-title">{t('profile.loadErrorTitle')}</CardTitle>
            <CardDescription role="alert">{t('profile.loadError')}</CardDescription>
          </CardHeader>
          <CardContent>
            <Button type="button" onClick={() => void profile.refetch()}>
              {t('profile.retry')}
            </Button>
          </CardContent>
        </Card>
      </section>
    )
  }

  return <ProfileView profile={profile.data} />
}

export { ProfilePage }
