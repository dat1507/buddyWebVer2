import { useId, useRef, useState } from 'react'
import {
  Check,
  CircleAlert,
  Clock3,
  Inbox,
  LoaderCircle,
  MessageCircle,
  SendHorizontal,
  Trash2,
  X,
} from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { Link } from 'react-router'

import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Typography } from '@/components/ui/typography'
import { invitationErrorKey } from '@/features/matching/invitation'
import type {
  IncomingInvitation,
  InvitationProfile,
  SentInvitation,
} from '@/features/matching/invitation'
import {
  CompatibilityDetails,
  MatchingProfileDetails,
} from '@/features/matching/matching-profile-details'
import {
  useAcceptInvitation,
  useCancelInvitation,
  useDeclineInvitation,
  useHideInvitation,
} from '@/features/matching/queries/use-invitations'
import type {
  IncomingInvitationsQuery,
  SentInvitationsQuery,
} from '@/features/matching/queries/use-invitations'
import { RecommendationAvatar } from '@/features/matching/recommendation-avatar'
import type { CatalogLocale } from '@/features/profile/profile-catalog'

function formatDateTime(value: string, locale: CatalogLocale): string {
  return new Intl.DateTimeFormat(locale, {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(new Date(value))
}

function InvitationProfileHeader({
  profile,
  score,
  titleId,
}: {
  profile: InvitationProfile
  score: number | null
  titleId: string
}) {
  const { t } = useTranslation()
  const name = profile.display_name?.trim() || t('recommendedBuddies.unnamed')
  return (
    <CardHeader className="gap-4 sm:flex-row sm:items-start">
      <RecommendationAvatar profile={profile} />
      <div className="min-w-0 flex-1 space-y-1">
        <CardTitle id={titleId} className="break-words">
          {name}
        </CardTitle>
        <CardDescription>
          {profile.student_type
            ? t(`recommendedBuddies.studentTypes.${profile.student_type}`)
            : t('invitations.profile.typeUnavailable')}
        </CardDescription>
        <CardDescription className="break-words">
          {profile.major?.trim() || t('recommendedBuddies.majorNotShared')}
        </CardDescription>
      </div>
      {score === null ? null : (
        <div className="shrink-0 rounded-2xl bg-vgu-orange/10 px-4 py-3 text-center text-vgu-orange-dark">
          <div className="text-xl font-bold tabular-nums">{score}%</div>
          <div className="text-xs font-semibold">{t('recommendedBuddies.compatibility')}</div>
        </div>
      )}
    </CardHeader>
  )
}

function InvitationContext({
  invitation,
  profile,
  locale,
  titleId,
}: {
  invitation: IncomingInvitation | SentInvitation
  profile: InvitationProfile
  locale: CatalogLocale
  titleId: string
}) {
  const { t } = useTranslation()
  return (
    <div className="grid min-w-0 gap-6 lg:grid-cols-2">
      <MatchingProfileDetails profile={profile} />
      {invitation.explanation ? (
        <CompatibilityDetails
          explanation={invitation.explanation}
          locale={locale}
          headingId={`${titleId}-compatibility`}
        />
      ) : (
        <section className="rounded-2xl border border-border/70 bg-muted/35 p-4">
          <Typography as="h3" variant="h4">
            {t('recommendedBuddies.compatibilityBreakdown')}
          </Typography>
          <Typography variant="muted" className="mt-1">
            {t('invitations.compatibilityUnavailable')}
          </Typography>
        </section>
      )}
    </div>
  )
}

function IncomingInvitationCard({
  invitation,
  locale,
}: {
  invitation: IncomingInvitation
  locale: CatalogLocale
}) {
  const { t } = useTranslation()
  const titleId = useId()
  const busyRef = useRef(false)
  const [action, setAction] = useState<'accept' | 'decline' | null>(null)
  const [errorKey, setErrorKey] = useState<string | null>(null)
  const accept = useAcceptInvitation()
  const decline = useDeclineInvitation()
  const busy = action !== null

  const run = async (nextAction: 'accept' | 'decline') => {
    if (busyRef.current) return
    busyRef.current = true
    setAction(nextAction)
    setErrorKey(null)
    try {
      if (nextAction === 'accept') await accept.mutateAsync(invitation.id)
      else await decline.mutateAsync(invitation.id)
    } catch (error) {
      setErrorKey(invitationErrorKey(error, nextAction))
    } finally {
      busyRef.current = false
      setAction(null)
    }
  }

  return (
    <Card role="article" aria-labelledby={titleId} aria-busy={busy} className="overflow-hidden">
      <InvitationProfileHeader
        profile={invitation.sender}
        score={invitation.score}
        titleId={titleId}
      />
      <CardContent className="space-y-6">
        <div className="rounded-2xl border border-vgu-orange/25 bg-vgu-orange/5 p-4">
          <Typography as="h3" variant="h4">
            {t('invitations.incoming.messageTitle')}
          </Typography>
          <p className="mt-2 whitespace-pre-wrap break-words text-sm leading-6">
            {invitation.message || t('invitations.incoming.emptyMessage')}
          </p>
        </div>
        <div className="flex flex-wrap gap-x-6 gap-y-2 text-sm text-muted-foreground">
          <span>
            {t('invitations.sentAt', { date: formatDateTime(invitation.created_at, locale) })}
          </span>
          <span className="flex items-center gap-1.5">
            <Clock3 aria-hidden="true" className="size-4" />
            {t('invitations.expiresAt', {
              date: formatDateTime(invitation.expires_at, locale),
            })}
          </span>
        </div>
        <InvitationContext
          invitation={invitation}
          profile={invitation.sender}
          locale={locale}
          titleId={titleId}
        />
        {errorKey ? (
          <p role="alert" className="text-sm text-destructive">
            {t(`invitations.errors.${errorKey}`)}
          </p>
        ) : null}
        <div className="flex flex-wrap gap-3" aria-live="polite">
          <Button type="button" disabled={busy} onClick={() => void run('accept')}>
            {action === 'accept' ? (
              <LoaderCircle
                aria-hidden="true"
                className="animate-spin motion-reduce:animate-none"
              />
            ) : (
              <Check aria-hidden="true" />
            )}
            {action === 'accept'
              ? t('invitations.actions.accepting')
              : t('invitations.actions.accept')}
          </Button>
          <Button
            type="button"
            variant="outline"
            disabled={busy}
            onClick={() => void run('decline')}
          >
            {action === 'decline' ? (
              <LoaderCircle
                aria-hidden="true"
                className="animate-spin motion-reduce:animate-none"
              />
            ) : (
              <X aria-hidden="true" />
            )}
            {action === 'decline'
              ? t('invitations.actions.declining')
              : t('invitations.actions.decline')}
          </Button>
        </div>
      </CardContent>
    </Card>
  )
}

function SentInvitationCard({
  invitation,
  locale,
}: {
  invitation: SentInvitation
  locale: CatalogLocale
}) {
  const { t } = useTranslation()
  const titleId = useId()
  const busyRef = useRef(false)
  const [busy, setBusy] = useState(false)
  const [errorKey, setErrorKey] = useState<string | null>(null)
  const cancel = useCancelInvitation()
  const hide = useHideInvitation()

  const run = async () => {
    if (busyRef.current) return
    busyRef.current = true
    setBusy(true)
    setErrorKey(null)
    const action = invitation.status === 'PENDING' ? 'cancel' : 'hide'
    try {
      if (action === 'cancel') await cancel.mutateAsync(invitation.id)
      else await hide.mutateAsync(invitation.id)
    } catch (error) {
      setErrorKey(invitationErrorKey(error, action))
    } finally {
      busyRef.current = false
      setBusy(false)
    }
  }

  return (
    <Card role="article" aria-labelledby={titleId} aria-busy={busy} className="overflow-hidden">
      <InvitationProfileHeader
        profile={invitation.recipient}
        score={invitation.score}
        titleId={titleId}
      />
      <CardContent className="space-y-6">
        <div className="flex flex-wrap items-center gap-x-6 gap-y-2 text-sm text-muted-foreground">
          <span className="rounded-full border border-border px-3 py-1 font-semibold text-foreground">
            {t(`invitations.status.${invitation.status}`)}
          </span>
          <span>
            {t('invitations.sentAt', { date: formatDateTime(invitation.created_at, locale) })}
          </span>
          {invitation.status === 'PENDING' ? (
            <span className="flex items-center gap-1.5">
              <Clock3 aria-hidden="true" className="size-4" />
              {t('invitations.expiresAt', {
                date: formatDateTime(invitation.expires_at, locale),
              })}
            </span>
          ) : null}
        </div>
        <InvitationContext
          invitation={invitation}
          profile={invitation.recipient}
          locale={locale}
          titleId={titleId}
        />
        {invitation.status === 'ACCEPTED' ? (
          <p className="rounded-xl border border-emerald-500/30 bg-emerald-500/10 p-3 text-sm">
            {t('invitations.sent.acceptedHelp')}
          </p>
        ) : null}
        {errorKey ? (
          <p role="alert" className="text-sm text-destructive">
            {t(`invitations.errors.${errorKey}`)}
          </p>
        ) : null}
        <div className="flex flex-wrap gap-3" aria-live="polite">
          {invitation.status === 'PENDING' ? (
            <Button type="button" variant="outline" disabled={busy} onClick={() => void run()}>
              {busy ? (
                <LoaderCircle
                  aria-hidden="true"
                  className="animate-spin motion-reduce:animate-none"
                />
              ) : (
                <X aria-hidden="true" />
              )}
              {busy ? t('invitations.actions.cancelling') : t('invitations.actions.cancel')}
            </Button>
          ) : (
            <>
              <Button asChild variant="outline">
                <Link to="/user/buddy">
                  <MessageCircle aria-hidden="true" />
                  {t('invitations.actions.startChatting')}
                </Link>
              </Button>
              <Button type="button" variant="outline" disabled={busy} onClick={() => void run()}>
                {busy ? (
                  <LoaderCircle
                    aria-hidden="true"
                    className="animate-spin motion-reduce:animate-none"
                  />
                ) : (
                  <Trash2 aria-hidden="true" />
                )}
                {busy ? t('invitations.actions.hiding') : t('invitations.actions.hide')}
              </Button>
            </>
          )}
        </div>
      </CardContent>
    </Card>
  )
}

function InvitationListError({ retry }: { retry: () => void }) {
  const { t } = useTranslation()
  return (
    <Card className="border-destructive/40">
      <CardHeader>
        <CircleAlert aria-hidden="true" className="size-6 text-destructive" />
        <CardTitle>{t('invitations.listErrorTitle')}</CardTitle>
        <CardDescription role="alert">{t('invitations.listError')}</CardDescription>
      </CardHeader>
      <CardContent>
        <Button type="button" onClick={retry}>
          {t('invitations.retry')}
        </Button>
      </CardContent>
    </Card>
  )
}

function InvitationSections({
  enabled,
  locale,
  incoming,
  sent,
  incomingItems,
  sentItems,
}: {
  enabled: boolean
  locale: CatalogLocale
  incoming: IncomingInvitationsQuery
  sent: SentInvitationsQuery
  incomingItems: IncomingInvitation[]
  sentItems: SentInvitation[]
}) {
  const { t } = useTranslation()

  if (!enabled) return null

  return (
    <section className="space-y-8" aria-labelledby="invitation-sections-title">
      <div>
        <Typography as="h2" variant="h3" id="invitation-sections-title">
          {t('invitations.title')}
        </Typography>
        <Typography variant="muted" className="mt-1">
          {t('invitations.subtitle')}
        </Typography>
      </div>

      <section className="space-y-4" aria-labelledby="incoming-invitations-title">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <Typography as="h3" variant="h4" id="incoming-invitations-title">
            {t('invitations.incoming.title')}
          </Typography>
          {incoming.isFetching && !incoming.isPending ? (
            <span role="status" className="flex items-center gap-2 text-sm text-muted-foreground">
              <LoaderCircle aria-hidden="true" className="size-4 animate-spin" />
              {t('invitations.updating')}
            </span>
          ) : null}
        </div>
        {incoming.isPending ? (
          <div className="flex min-h-32 items-center justify-center gap-2 text-muted-foreground">
            <LoaderCircle aria-hidden="true" className="size-5 animate-spin" />
            <span role="status">{t('invitations.incoming.loading')}</span>
          </div>
        ) : incoming.isError ? (
          <InvitationListError retry={() => void incoming.refetch()} />
        ) : incomingItems.length === 0 ? (
          <Card className="text-center">
            <CardHeader>
              <Inbox aria-hidden="true" className="mx-auto size-7 text-vgu-orange" />
              <CardTitle>{t('invitations.incoming.emptyTitle')}</CardTitle>
              <CardDescription>{t('invitations.incoming.emptyDescription')}</CardDescription>
            </CardHeader>
          </Card>
        ) : (
          <div className="space-y-5">
            {incomingItems.map((invitation) => (
              <IncomingInvitationCard key={invitation.id} invitation={invitation} locale={locale} />
            ))}
          </div>
        )}
        {incoming.hasNextPage ? (
          <Button
            type="button"
            variant="outline"
            disabled={incoming.isFetchingNextPage}
            onClick={() => void incoming.fetchNextPage()}
          >
            {incoming.isFetchingNextPage ? (
              <LoaderCircle aria-hidden="true" className="animate-spin" />
            ) : null}
            {incoming.isFetchingNextPage ? t('invitations.loadingMore') : t('invitations.loadMore')}
          </Button>
        ) : incomingItems.length > 0 ? (
          <p className="text-sm text-muted-foreground">{t('invitations.end')}</p>
        ) : null}
      </section>

      <section className="space-y-4" aria-labelledby="sent-invitations-title">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <Typography as="h3" variant="h4" id="sent-invitations-title">
            {t('invitations.sent.title')}
          </Typography>
          {sent.isFetching && !sent.isPending ? (
            <span role="status" className="flex items-center gap-2 text-sm text-muted-foreground">
              <LoaderCircle aria-hidden="true" className="size-4 animate-spin" />
              {t('invitations.updating')}
            </span>
          ) : null}
        </div>
        {sent.isPending ? (
          <div className="flex min-h-32 items-center justify-center gap-2 text-muted-foreground">
            <LoaderCircle aria-hidden="true" className="size-5 animate-spin" />
            <span role="status">{t('invitations.sent.loading')}</span>
          </div>
        ) : sent.isError ? (
          <InvitationListError retry={() => void sent.refetch()} />
        ) : sentItems.length === 0 ? (
          <Card className="text-center">
            <CardHeader>
              <SendHorizontal aria-hidden="true" className="mx-auto size-7 text-vgu-orange" />
              <CardTitle>{t('invitations.sent.emptyTitle')}</CardTitle>
              <CardDescription>{t('invitations.sent.emptyDescription')}</CardDescription>
            </CardHeader>
          </Card>
        ) : (
          <div className="space-y-5">
            {sentItems.map((invitation) => (
              <SentInvitationCard key={invitation.id} invitation={invitation} locale={locale} />
            ))}
          </div>
        )}
        {sent.hasNextPage ? (
          <Button
            type="button"
            variant="outline"
            disabled={sent.isFetchingNextPage}
            onClick={() => void sent.fetchNextPage()}
          >
            {sent.isFetchingNextPage ? (
              <LoaderCircle aria-hidden="true" className="animate-spin" />
            ) : null}
            {sent.isFetchingNextPage ? t('invitations.loadingMore') : t('invitations.loadMore')}
          </Button>
        ) : sentItems.length > 0 ? (
          <p className="text-sm text-muted-foreground">{t('invitations.end')}</p>
        ) : null}
      </section>
    </section>
  )
}

export { InvitationSections }
