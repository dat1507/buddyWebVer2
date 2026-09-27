import { useId, useState } from 'react'
import {
  CalendarClock,
  ChevronLeft,
  ChevronRight,
  CircleAlert,
  Languages,
  LoaderCircle,
  LockKeyhole,
  Sparkles,
  Users,
} from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { Link } from 'react-router'

import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Typography } from '@/components/ui/typography'
import { RecommendationAvatar } from '@/features/matching/recommendation-avatar'
import type {
  CompatibilityExplanation,
  CompatibilitySignal,
  MatchingAvailability,
  MatchingLanguage,
  MatchingPreference,
  Recommendation,
} from '@/features/matching/recommendation'
import { RECOMMENDATION_PAGE_SIZE } from '@/features/matching/recommendation'
import { useRecommendations } from '@/features/matching/queries/use-recommendations'
import type { CatalogLocale } from '@/features/profile/profile-catalog'
import { useProfileCompletion } from '@/features/profile/queries/use-own-profile'
import { ApiError } from '@/lib/api'

const compatibilitySignals = [
  'interests',
  'activities',
  'availability',
  'languages',
  'major',
] as const satisfies readonly (keyof CompatibilityExplanation)[]

function catalogLocale(language: string | undefined): CatalogLocale {
  return language?.split('-')[0] === 'de' ? 'de' : 'en'
}

function formatNumber(value: number, locale: CatalogLocale): string {
  return new Intl.NumberFormat(locale, { maximumFractionDigits: 2 }).format(value)
}

function formatReferenceWeek(value: string, locale: CatalogLocale): string {
  return new Intl.DateTimeFormat(locale, { dateStyle: 'medium', timeZone: 'UTC' }).format(
    new Date(`${value}T00:00:00.000Z`),
  )
}

function minuteLabel(minutes: number): string {
  if (minutes === 1440) return '24:00'
  return `${String(Math.floor(minutes / 60)).padStart(2, '0')}:${String(minutes % 60).padStart(2, '0')}`
}

function PreferenceList({
  label,
  values,
}: {
  label: string
  values: readonly MatchingPreference[]
}) {
  const { t } = useTranslation()

  return (
    <div className="space-y-2">
      <Typography variant="small" className="font-semibold">
        {label}
      </Typography>
      {values.length > 0 ? (
        <ul aria-label={label} className="flex flex-wrap gap-2">
          {values.map((value) => (
            <li
              key={value.id ?? `custom:${value.label}`}
              className="max-w-full break-words rounded-full border border-border bg-background px-3 py-1 text-xs font-medium"
            >
              {value.label}
              {value.is_custom ? (
                <span className="sr-only"> {t('recommendedBuddies.customPreference')}</span>
              ) : null}
            </li>
          ))}
        </ul>
      ) : (
        <Typography variant="muted">{t('recommendedBuddies.noneShared')}</Typography>
      )}
    </div>
  )
}

function LanguageList({ values }: { values: readonly MatchingLanguage[] }) {
  const { t } = useTranslation()
  const label = t('recommendedBuddies.languages')

  return (
    <div className="space-y-2">
      <Typography variant="small" className="flex items-center gap-2 font-semibold">
        <Languages aria-hidden="true" className="size-4" />
        {label}
      </Typography>
      <ul aria-label={label} className="flex flex-wrap gap-2">
        {values.map((value) => (
          <li
            key={value.code ?? `custom:${value.label}`}
            className="max-w-full break-words rounded-full border border-border bg-background px-3 py-1 text-xs font-medium"
          >
            {t('recommendedBuddies.languageValue', {
              language: value.label,
              proficiency: t(`recommendedBuddies.proficiencies.${value.proficiency}`),
            })}
            {value.is_custom ? (
              <span className="sr-only"> {t('recommendedBuddies.customPreference')}</span>
            ) : null}
          </li>
        ))}
      </ul>
    </div>
  )
}

function Availability({ availability }: { availability: MatchingAvailability | null }) {
  const { t } = useTranslation()

  return (
    <div className="space-y-2">
      <Typography variant="small" className="flex items-center gap-2 font-semibold">
        <CalendarClock aria-hidden="true" className="size-4" />
        {t('recommendedBuddies.availability')}
      </Typography>
      {!availability || availability.slots.length === 0 ? (
        <Typography variant="muted">{t('recommendedBuddies.noAvailability')}</Typography>
      ) : (
        <div className="space-y-2">
          <Typography variant="muted" className="break-all">
            {t('recommendedBuddies.timezone', { timezone: availability.timezone })}
          </Typography>
          <ul
            className="grid gap-1 text-sm sm:grid-cols-2"
            aria-label={t('recommendedBuddies.availability')}
          >
            {availability.slots.map((slot, index) => (
              <li key={`${slot.weekday}:${slot.start_minute}:${slot.end_minute}:${index}`}>
                {t('recommendedBuddies.availabilityValue', {
                  day: t(`recommendedBuddies.weekdays.${slot.weekday}`),
                  start: minuteLabel(slot.start_minute),
                  end: minuteLabel(slot.end_minute),
                })}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  )
}

function CompatibilityRow({
  name,
  signal,
  locale,
}: {
  name: keyof CompatibilityExplanation
  signal: CompatibilitySignal
  locale: CatalogLocale
}) {
  const { t } = useTranslation()
  const label = t(`recommendedBuddies.signals.${name}`)

  return (
    <li className="space-y-1.5">
      <div className="flex items-center justify-between gap-3 text-sm">
        <span>{label}</span>
        <span className="whitespace-nowrap font-semibold">
          {t('recommendedBuddies.signalDetails', {
            similarity: formatNumber(signal.similarity * 100, locale),
            points: formatNumber(signal.points, locale),
            weight: signal.weight,
          })}
        </span>
      </div>
      <progress
        aria-label={t('recommendedBuddies.signalProgress', { signal: label })}
        className="h-2 w-full accent-vgu-orange"
        max={signal.weight || 1}
        value={signal.points}
      />
    </li>
  )
}

function RecommendationCard({
  recommendation,
  locale,
}: {
  recommendation: Recommendation
  locale: CatalogLocale
}) {
  const { t } = useTranslation()
  const name = recommendation.profile.display_name?.trim() || t('recommendedBuddies.unnamed')
  const titleId = useId()

  return (
    <Card role="article" aria-labelledby={titleId} className="min-w-0 overflow-hidden">
      <CardHeader className="gap-4 sm:flex-row sm:items-start">
        <RecommendationAvatar profile={recommendation.profile} />
        <div className="min-w-0 flex-1 space-y-3">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div className="min-w-0 space-y-1">
              <CardTitle id={titleId} className="break-words">
                {name}
              </CardTitle>
              <CardDescription>
                {t(`recommendedBuddies.studentTypes.${recommendation.profile.student_type}`)}
              </CardDescription>
              <CardDescription className="break-words">
                {recommendation.profile.major?.trim() || t('recommendedBuddies.majorNotShared')}
              </CardDescription>
            </div>
            <div className="rounded-2xl bg-vgu-orange/10 px-4 py-3 text-center text-vgu-orange-dark">
              <div className="text-2xl font-bold tabular-nums">{recommendation.score}%</div>
              <div className="text-xs font-semibold">{t('recommendedBuddies.compatibility')}</div>
            </div>
          </div>
          <progress
            aria-label={t('recommendedBuddies.overallCompatibility', { name })}
            className="h-2 w-full accent-vgu-orange"
            max={100}
            value={recommendation.score}
          />
        </div>
      </CardHeader>
      <CardContent className="grid min-w-0 gap-6 lg:grid-cols-2">
        <section className="space-y-5" aria-label={t('recommendedBuddies.profileInformation')}>
          <PreferenceList
            label={t('recommendedBuddies.interests')}
            values={recommendation.profile.interests}
          />
          <PreferenceList
            label={t('recommendedBuddies.activities')}
            values={recommendation.profile.activities}
          />
          <LanguageList values={recommendation.profile.languages} />
          <Availability availability={recommendation.profile.availability} />
        </section>
        <section
          className="rounded-2xl border border-border/70 bg-muted/35 p-4"
          aria-labelledby={`${titleId}-compatibility`}
        >
          <Typography as="h3" variant="h4" id={`${titleId}-compatibility`}>
            {t('recommendedBuddies.compatibilityBreakdown')}
          </Typography>
          <Typography variant="muted" className="mt-1">
            {t('recommendedBuddies.compatibilityDescription')}
          </Typography>
          <ul className="mt-4 space-y-3">
            {compatibilitySignals.map((signal) => (
              <CompatibilityRow
                key={signal}
                name={signal}
                signal={recommendation.explanation[signal]}
                locale={locale}
              />
            ))}
          </ul>
        </section>
      </CardContent>
    </Card>
  )
}

function LockedRecommendations() {
  const { t } = useTranslation()
  const completion = useProfileCompletion()
  const requiresVerification = completion.data?.reasons.includes('EMAIL_VERIFICATION_REQUIRED')

  return (
    <Card className="mx-auto max-w-2xl border-amber-500/40">
      <CardHeader>
        <LockKeyhole aria-hidden="true" className="size-6 text-amber-600" />
        <CardTitle>{t('recommendedBuddies.lockedTitle')}</CardTitle>
        <CardDescription>
          {t(
            requiresVerification
              ? 'recommendedBuddies.lockedVerification'
              : 'recommendedBuddies.lockedPreferences',
          )}
        </CardDescription>
      </CardHeader>
      <CardContent>
        <Button asChild variant="outline">
          <Link to={requiresVerification ? '/user/settings' : '/user/profile/edit'}>
            {t(
              requiresVerification
                ? 'recommendedBuddies.manageVerification'
                : 'recommendedBuddies.updatePreferences',
            )}
          </Link>
        </Button>
      </CardContent>
    </Card>
  )
}

function RecommendationError({ retry }: { retry: () => void }) {
  const { t } = useTranslation()

  return (
    <Card className="mx-auto max-w-2xl border-destructive/40">
      <CardHeader>
        <CircleAlert aria-hidden="true" className="size-6 text-destructive" />
        <CardTitle>{t('recommendedBuddies.errorTitle')}</CardTitle>
        <CardDescription role="alert">{t('recommendedBuddies.error')}</CardDescription>
      </CardHeader>
      <CardContent>
        <Button type="button" onClick={retry}>
          {t('recommendedBuddies.retry')}
        </Button>
      </CardContent>
    </Card>
  )
}

function MatchingPage() {
  const { t, i18n } = useTranslation()
  const locale = catalogLocale(i18n.resolvedLanguage)
  const [pagination, setPagination] = useState<{ locale: CatalogLocale; page: number }>({
    locale,
    page: 1,
  })
  const page = pagination.locale === locale ? pagination.page : 1
  const titleId = useId()
  const resultsTitleId = useId()
  const completion = useProfileCompletion()
  const eligible = completion.data?.matching_eligible === true
  const recommendations = useRecommendations({
    enabled: eligible,
    locale,
    page,
    pageSize: RECOMMENDATION_PAGE_SIZE,
  })

  const error = recommendations.error
  const lockedByServer = error instanceof ApiError && error.code === 'forbidden'

  return (
    <section
      aria-labelledby={titleId}
      className="min-w-0 space-y-6 py-6"
      aria-busy={eligible && recommendations.isFetching}
    >
      <header className="space-y-2">
        <Typography
          variant="small"
          className="font-semibold uppercase tracking-[0.18em] text-vgu-orange"
        >
          {t('recommendedBuddies.eyebrow')}
        </Typography>
        <Typography as="h1" variant="h2" id={titleId}>
          {t('recommendedBuddies.title')}
        </Typography>
        <Typography variant="lead" className="max-w-3xl">
          {t('recommendedBuddies.subtitle')}
        </Typography>
      </header>

      <Typography as="h2" variant="h3" id={resultsTitleId} className="sr-only">
        {t('recommendedBuddies.resultsTitle')}
      </Typography>

      {!eligible || lockedByServer ? (
        <LockedRecommendations />
      ) : recommendations.isPending ? (
        <div className="flex min-h-64 items-center justify-center gap-3 text-muted-foreground">
          <LoaderCircle
            aria-hidden="true"
            className="size-5 animate-spin motion-reduce:animate-none"
          />
          <span role="status">{t('recommendedBuddies.loading')}</span>
        </div>
      ) : recommendations.isError ? (
        <RecommendationError retry={() => void recommendations.refetch()} />
      ) : recommendations.data.items.length === 0 ? (
        <Card className="mx-auto max-w-2xl text-center">
          <CardHeader>
            <Users aria-hidden="true" className="mx-auto size-8 text-vgu-orange" />
            <CardTitle>{t('recommendedBuddies.emptyTitle')}</CardTitle>
            <CardDescription>{t('recommendedBuddies.emptyDescription')}</CardDescription>
          </CardHeader>
        </Card>
      ) : (
        <>
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <Typography variant="muted">
                {t('recommendedBuddies.resultSummary', {
                  count: recommendations.data.items.length,
                  total: recommendations.data.total,
                })}
              </Typography>
              <Typography variant="muted" className="text-xs">
                {t('recommendedBuddies.referenceWeek', {
                  date: formatReferenceWeek(recommendations.data.reference_week_start, locale),
                })}
              </Typography>
            </div>
            {recommendations.isFetching ? (
              <span role="status" className="flex items-center gap-2 text-sm text-muted-foreground">
                <LoaderCircle
                  aria-hidden="true"
                  className="size-4 animate-spin motion-reduce:animate-none"
                />
                {t('recommendedBuddies.updating')}
              </span>
            ) : null}
          </div>
          <div className="space-y-5">
            {recommendations.data.items.map((recommendation) => (
              <RecommendationCard
                key={recommendation.profile.id}
                recommendation={recommendation}
                locale={locale}
              />
            ))}
          </div>
          <nav
            aria-label={t('recommendedBuddies.paginationLabel')}
            className="flex flex-wrap items-center justify-between gap-3"
          >
            <Button
              type="button"
              variant="outline"
              disabled={page <= 1 || recommendations.isFetching}
              onClick={() => setPagination({ locale, page: Math.max(1, page - 1) })}
            >
              <ChevronLeft aria-hidden="true" />
              {t('recommendedBuddies.previous')}
            </Button>
            <span className="text-sm font-semibold" aria-live="polite">
              {t('recommendedBuddies.page', {
                page: recommendations.data.page,
                totalPages: recommendations.data.total_pages,
              })}
            </span>
            <Button
              type="button"
              variant="outline"
              disabled={page >= recommendations.data.total_pages || recommendations.isFetching}
              onClick={() => setPagination({ locale, page: page + 1 })}
            >
              {t('recommendedBuddies.next')}
              <ChevronRight aria-hidden="true" />
            </Button>
          </nav>
          {page >= recommendations.data.total_pages ? (
            <p className="text-center text-sm text-muted-foreground">
              <Sparkles aria-hidden="true" className="mr-2 inline size-4" />
              {t('recommendedBuddies.end')}
            </p>
          ) : null}
        </>
      )}
    </section>
  )
}

export { MatchingPage }
