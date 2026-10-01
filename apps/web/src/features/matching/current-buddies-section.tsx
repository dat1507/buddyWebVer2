import { useEffect, useId, useMemo, useRef } from 'react'
import {
  CircleAlert,
  HeartHandshake,
  LoaderCircle,
  LockKeyhole,
  MessageCircle,
  Users,
} from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { Link } from 'react-router'

import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Typography } from '@/components/ui/typography'
import { currentBuddyPath } from '@/features/matching/current-buddy'
import type { CurrentBuddy } from '@/features/matching/current-buddy'
import {
  CompatibilityDetails,
  MatchingProfileDetails,
} from '@/features/matching/matching-profile-details'
import { uniqueCurrentBuddies } from '@/features/matching/queries/use-current-buddies'
import type { CurrentBuddiesQuery } from '@/features/matching/queries/use-current-buddies'
import { RecommendationAvatar } from '@/features/matching/recommendation-avatar'
import type { CatalogLocale } from '@/features/profile/profile-catalog'
import { ApiError } from '@/lib/api'

function formatReferenceWeek(value: string, locale: CatalogLocale): string {
  return new Intl.DateTimeFormat(locale, { dateStyle: 'medium', timeZone: 'UTC' }).format(
    new Date(`${value}T00:00:00.000Z`),
  )
}

function CurrentBuddyCard({
  currentBuddy,
  focused,
  locale,
}: {
  currentBuddy: CurrentBuddy
  focused: boolean
  locale: CatalogLocale
}) {
  const { t } = useTranslation()
  const titleId = useId()
  const cardRef = useRef<HTMLDivElement>(null)
  const name = currentBuddy.buddy.display_name?.trim() || t('recommendedBuddies.unnamed')

  useEffect(() => {
    if (focused) cardRef.current?.focus({ preventScroll: true })
  }, [focused])

  return (
    <Card
      ref={cardRef}
      role="article"
      aria-labelledby={titleId}
      tabIndex={focused ? -1 : undefined}
      className={
        focused
          ? 'min-w-0 overflow-hidden ring-2 ring-vgu-orange ring-offset-2 ring-offset-background'
          : 'min-w-0 overflow-hidden'
      }
    >
      <CardHeader className="gap-4 sm:flex-row sm:items-start">
        <RecommendationAvatar profile={currentBuddy.buddy} />
        <div className="min-w-0 flex-1 space-y-3">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div className="min-w-0 space-y-1">
              <CardTitle id={titleId} className="break-words">
                {name}
              </CardTitle>
              <CardDescription>
                {currentBuddy.buddy.student_type
                  ? t(`recommendedBuddies.studentTypes.${currentBuddy.buddy.student_type}`)
                  : t('currentBuddies.typeUnavailable')}
              </CardDescription>
              <CardDescription className="break-words">
                {currentBuddy.buddy.major?.trim() || t('recommendedBuddies.majorNotShared')}
              </CardDescription>
            </div>
            <div className="shrink-0 rounded-2xl bg-vgu-orange/10 px-4 py-3 text-center text-vgu-orange-dark">
              <div className="text-2xl font-bold tabular-nums">{currentBuddy.score}%</div>
              <div className="text-xs font-semibold">{t('recommendedBuddies.compatibility')}</div>
            </div>
          </div>
          <progress
            aria-label={t('recommendedBuddies.overallCompatibility', { name })}
            className="h-2 w-full accent-vgu-orange"
            max={100}
            value={currentBuddy.score}
          />
          <Typography variant="muted" className="text-xs">
            {t('currentBuddies.referenceWeek', {
              date: formatReferenceWeek(currentBuddy.reference_week_start, locale),
            })}
          </Typography>
        </div>
      </CardHeader>
      <CardContent className="grid min-w-0 gap-6 lg:grid-cols-2">
        <MatchingProfileDetails profile={currentBuddy.buddy} />
        <CompatibilityDetails
          explanation={currentBuddy.explanation}
          locale={locale}
          headingId={`${titleId}-compatibility`}
        />
        <div className="flex flex-wrap items-center justify-end gap-3 lg:col-span-2">
          <Button asChild>
            <Link
              to={currentBuddyPath(currentBuddy.conversation_id)}
              aria-label={t('currentBuddies.startChattingWithName', { name })}
            >
              <MessageCircle aria-hidden="true" />
              {t('currentBuddies.startChatting')}
            </Link>
          </Button>
        </div>
      </CardContent>
    </Card>
  )
}

function CurrentBuddiesError({ retry }: { retry: () => void }) {
  const { t } = useTranslation()
  return (
    <Card className="border-destructive/40">
      <CardHeader>
        <CircleAlert aria-hidden="true" className="size-6 text-destructive" />
        <CardTitle>{t('currentBuddies.errorTitle')}</CardTitle>
        <CardDescription role="alert">{t('currentBuddies.error')}</CardDescription>
      </CardHeader>
      <CardContent>
        <Button type="button" onClick={retry}>
          {t('currentBuddies.retry')}
        </Button>
      </CardContent>
    </Card>
  )
}

function CurrentBuddiesLocked() {
  const { t } = useTranslation()
  return (
    <Card className="border-amber-500/40">
      <CardHeader>
        <LockKeyhole aria-hidden="true" className="size-6 text-amber-600" />
        <CardTitle>{t('currentBuddies.lockedTitle')}</CardTitle>
        <CardDescription>{t('currentBuddies.lockedDescription')}</CardDescription>
      </CardHeader>
      <CardContent>
        <Button asChild variant="outline">
          <Link to="/user/settings">{t('currentBuddies.manageVerification')}</Link>
        </Button>
      </CardContent>
    </Card>
  )
}

function CurrentBuddiesSection({
  enabled,
  locale,
  query,
  targetConversationId,
}: {
  enabled: boolean
  locale: CatalogLocale
  query: CurrentBuddiesQuery
  targetConversationId: string | null
}) {
  const { t } = useTranslation()
  const {
    data,
    error,
    fetchNextPage,
    hasNextPage,
    isError,
    isFetching,
    isFetchingNextPage,
    isPending,
    refetch,
  } = query
  const items = useMemo(() => uniqueCurrentBuddies(data?.pages), [data?.pages])
  const focusedBuddy = targetConversationId
    ? items.find(({ conversation_id: conversationId }) => conversationId === targetConversationId)
    : undefined
  const forbidden = error instanceof ApiError && error.code === 'forbidden'

  useEffect(() => {
    if (
      !targetConversationId ||
      focusedBuddy ||
      !hasNextPage ||
      isFetchingNextPage ||
      isPending ||
      isError
    ) {
      return
    }
    void fetchNextPage()
  }, [
    fetchNextPage,
    focusedBuddy,
    hasNextPage,
    isError,
    isFetchingNextPage,
    isPending,
    targetConversationId,
  ])

  const targetUnavailable =
    Boolean(targetConversationId) && !focusedBuddy && !isPending && !isError && !hasNextPage

  return (
    <section
      id="current-buddies"
      className="scroll-mt-6 space-y-5"
      aria-labelledby="current-buddies-title"
      aria-busy={enabled && isFetching}
    >
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <Typography as="h2" variant="h3" id="current-buddies-title">
            {t('currentBuddies.title')}
          </Typography>
          <Typography variant="muted" className="mt-1 max-w-3xl">
            {t('currentBuddies.subtitle')}
          </Typography>
        </div>
        {isFetching && !isPending && !isFetchingNextPage ? (
          <span role="status" className="flex items-center gap-2 text-sm text-muted-foreground">
            <LoaderCircle
              aria-hidden="true"
              className="size-4 animate-spin motion-reduce:animate-none"
            />
            {t('currentBuddies.updating')}
          </span>
        ) : null}
      </div>

      {!enabled || forbidden ? (
        <CurrentBuddiesLocked />
      ) : isPending ? (
        <div className="flex min-h-40 items-center justify-center gap-3 text-muted-foreground">
          <LoaderCircle
            aria-hidden="true"
            className="size-5 animate-spin motion-reduce:animate-none"
          />
          <span role="status">{t('currentBuddies.loading')}</span>
        </div>
      ) : isError ? (
        <CurrentBuddiesError retry={() => void refetch()} />
      ) : items.length === 0 ? (
        <Card className="text-center">
          <CardHeader>
            <HeartHandshake aria-hidden="true" className="mx-auto size-8 text-vgu-orange" />
            <CardTitle>{t('currentBuddies.emptyTitle')}</CardTitle>
            <CardDescription>{t('currentBuddies.emptyDescription')}</CardDescription>
          </CardHeader>
        </Card>
      ) : (
        <div className="space-y-5">
          <Typography variant="muted">
            {t('currentBuddies.resultSummary', {
              count: items.length,
              total: data?.pages[0]?.total ?? items.length,
            })}
          </Typography>
          {items.map((currentBuddy) => (
            <CurrentBuddyCard
              key={currentBuddy.match_id}
              currentBuddy={currentBuddy}
              focused={currentBuddy.conversation_id === targetConversationId}
              locale={locale}
            />
          ))}
        </div>
      )}

      {targetUnavailable ? (
        <p role="status" className="rounded-xl border border-border bg-muted/35 p-3 text-sm">
          {t('currentBuddies.conversationUnavailable')}
        </p>
      ) : null}

      {hasNextPage ? (
        <Button
          type="button"
          variant="outline"
          disabled={isFetchingNextPage}
          onClick={() => void fetchNextPage()}
        >
          {isFetchingNextPage ? (
            <LoaderCircle aria-hidden="true" className="animate-spin motion-reduce:animate-none" />
          ) : (
            <Users aria-hidden="true" />
          )}
          {isFetchingNextPage ? t('currentBuddies.loadingMore') : t('currentBuddies.loadMore')}
        </Button>
      ) : items.length > 0 ? (
        <p className="text-sm text-muted-foreground">{t('currentBuddies.end')}</p>
      ) : null}
    </section>
  )
}

export { CurrentBuddiesSection }
