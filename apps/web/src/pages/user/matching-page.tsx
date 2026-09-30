import { useId, useMemo, useRef, useState } from 'react'
import {
  Check,
  ChevronLeft,
  ChevronRight,
  CircleAlert,
  LoaderCircle,
  LockKeyhole,
  Send,
  Sparkles,
  Users,
} from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { Link } from 'react-router'

import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Typography } from '@/components/ui/typography'
import { InvitationComposer } from '@/features/matching/invitation-composer'
import { InvitationSections } from '@/features/matching/invitation-sections'
import { invitationErrorKey } from '@/features/matching/invitation'
import {
  CompatibilityDetails,
  MatchingProfileDetails,
} from '@/features/matching/matching-profile-details'
import { RecommendationAvatar } from '@/features/matching/recommendation-avatar'
import type { Recommendation } from '@/features/matching/recommendation'
import { RECOMMENDATION_PAGE_SIZE } from '@/features/matching/recommendation'
import {
  uniqueIncomingItems,
  uniqueSentItems,
  useIncomingInvitations,
  useSendInvitation,
  useSentInvitations,
} from '@/features/matching/queries/use-invitations'
import { useRecommendations } from '@/features/matching/queries/use-recommendations'
import type { CatalogLocale } from '@/features/profile/profile-catalog'
import { useProfileCompletion } from '@/features/profile/queries/use-own-profile'
import { ApiError } from '@/lib/api'

function catalogLocale(language: string | undefined): CatalogLocale {
  return language?.split('-')[0] === 'de' ? 'de' : 'en'
}

function formatReferenceWeek(value: string, locale: CatalogLocale): string {
  return new Intl.DateTimeFormat(locale, { dateStyle: 'medium', timeZone: 'UTC' }).format(
    new Date(`${value}T00:00:00.000Z`),
  )
}

function RecommendationCard({
  recommendation,
  locale,
  invitationState,
  onInvite,
}: {
  recommendation: Recommendation
  locale: CatalogLocale
  invitationState: 'sent' | 'received' | null
  onInvite: (recommendation: Recommendation) => void
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
        <MatchingProfileDetails profile={recommendation.profile} />
        <CompatibilityDetails
          explanation={recommendation.explanation}
          locale={locale}
          headingId={`${titleId}-compatibility`}
        />
        <div className="flex flex-wrap items-center justify-end gap-3 lg:col-span-2">
          <Button
            type="button"
            disabled={invitationState !== null}
            onClick={() => onInvite(recommendation)}
          >
            {invitationState ? <Check aria-hidden="true" /> : <Send aria-hidden="true" />}
            {invitationState
              ? t(`invitations.recommendation.${invitationState}`)
              : t('invitations.recommendation.send')}
          </Button>
        </div>
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
  const [composerTarget, setComposerTarget] = useState<Recommendation | null>(null)
  const [composerErrorKey, setComposerErrorKey] = useState<string | null>(null)
  const [successName, setSuccessName] = useState<string | null>(null)
  const sendStartedRef = useRef(false)
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
  const sendInvitation = useSendInvitation()

  const error = recommendations.error
  const lockedByServer = error instanceof ApiError && error.code === 'forbidden'
  const invitationsEnabled = eligible && !lockedByServer
  const incomingInvitations = useIncomingInvitations({ enabled: invitationsEnabled, locale })
  const sentInvitations = useSentInvitations({ enabled: invitationsEnabled, locale })
  const incomingItems = useMemo(
    () => uniqueIncomingItems(incomingInvitations.data?.pages),
    [incomingInvitations.data?.pages],
  )
  const sentItems = useMemo(
    () => uniqueSentItems(sentInvitations.data?.pages),
    [sentInvitations.data?.pages],
  )
  const incomingProfileIds = useMemo(
    () => new Set(incomingItems.map(({ sender }) => sender.id)),
    [incomingItems],
  )
  const sentProfileIdsFromServer = useMemo(
    () => new Set(sentItems.map(({ recipient }) => recipient.id)),
    [sentItems],
  )

  const closeComposer = () => {
    if (sendInvitation.isPending) return
    setComposerTarget(null)
    setComposerErrorKey(null)
  }

  const submitInvitation = async (message: string) => {
    if (!composerTarget || sendStartedRef.current) return
    sendStartedRef.current = true
    setComposerErrorKey(null)
    setSuccessName(null)
    const target = composerTarget
    try {
      await sendInvitation.mutateAsync({
        recipientProfileId: target.profile.id,
        message,
      })
      setSuccessName(target.profile.display_name?.trim() || t('recommendedBuddies.unnamed'))
      setComposerTarget(null)
    } catch (submitError) {
      setComposerErrorKey(invitationErrorKey(submitError, 'send'))
    } finally {
      sendStartedRef.current = false
    }
  }

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

      {successName ? (
        <p
          role="status"
          className="rounded-xl border border-emerald-500/30 bg-emerald-500/10 px-4 py-3 text-sm"
        >
          {t('invitations.composer.success', { name: successName })}
        </p>
      ) : null}

      <InvitationSections
        enabled={invitationsEnabled}
        locale={locale}
        incoming={incomingInvitations}
        sent={sentInvitations}
        incomingItems={incomingItems}
        sentItems={sentItems}
      />

      <Typography as="h2" variant="h3" id={resultsTitleId}>
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
                invitationState={
                  incomingProfileIds.has(recommendation.profile.id)
                    ? 'received'
                    : sentProfileIdsFromServer.has(recommendation.profile.id)
                      ? 'sent'
                      : null
                }
                onInvite={(target) => {
                  setSuccessName(null)
                  setComposerErrorKey(null)
                  setComposerTarget(target)
                }}
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
      <InvitationComposer
        target={composerTarget?.profile ?? null}
        pending={sendInvitation.isPending}
        errorKey={composerErrorKey}
        onCancel={closeComposer}
        onSubmit={submitInvitation}
      />
    </section>
  )
}

export { MatchingPage }
