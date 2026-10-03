import { Link, Navigate, useLocation } from 'react-router'
import { ArrowLeft, LockKeyhole } from 'lucide-react'
import { useTranslation } from 'react-i18next'

import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { ChatConversation } from '@/features/chat/chat-conversation'
import { conversationIdFromBuddyLocation } from '@/features/matching/current-buddy'
import { CurrentBuddiesSection } from '@/features/matching/current-buddies-section'
import { useCurrentBuddies } from '@/features/matching/queries/use-current-buddies'
import type { CatalogLocale } from '@/features/profile/profile-catalog'
import { Typography } from '@/components/ui/typography'
import { useAuthStore } from '@/stores/auth-store'

function catalogLocale(language: string | undefined): CatalogLocale {
  return language?.split('-')[0] === 'de' ? 'de' : 'en'
}

function MyBuddyListPage({ enabled }: { enabled: boolean }) {
  const { t, i18n } = useTranslation()
  const locale = catalogLocale(i18n.resolvedLanguage)
  const currentBuddies = useCurrentBuddies({ enabled, locale })
  const titleId = 'my-buddy-title'
  return (
    <section aria-labelledby={titleId} className="min-w-0 space-y-6 py-6">
      <header className="space-y-2">
        <Typography
          variant="small"
          className="font-semibold uppercase tracking-[0.18em] text-vgu-orange"
        >
          {t('myBuddy.eyebrow')}
        </Typography>
        <Typography as="h1" variant="h2" id={titleId}>
          {t('myBuddy.title')}
        </Typography>
        <Typography variant="lead" className="max-w-3xl">
          {t('myBuddy.subtitle')}
        </Typography>
      </header>
      <CurrentBuddiesSection
        enabled={enabled}
        locale={locale}
        query={currentBuddies}
        targetConversationId={null}
      />
    </section>
  )
}

function CurrentBuddyRoutePage() {
  const { t } = useTranslation()
  const location = useLocation()
  const user = useAuthStore((state) => state.user)
  const conversationId = conversationIdFromBuddyLocation(location)
  if (!user) return null
  if (!conversationId) {
    if (location.search || location.hash) return <Navigate to="/user/buddy" replace />
    return <MyBuddyListPage enabled={user.email_verified} />
  }
  if (!user.email_verified) {
    return (
      <section className="min-w-0 py-6" aria-labelledby="chat-locked-title">
        <Card className="mx-auto max-w-2xl border-amber-500/40">
          <CardHeader>
            <LockKeyhole aria-hidden="true" className="size-6 text-amber-600" />
            <CardTitle id="chat-locked-title">{t('chat.locked.title')}</CardTitle>
            <CardDescription>{t('chat.locked.description')}</CardDescription>
          </CardHeader>
          <CardContent>
            <Button asChild variant="outline">
              <Link to="/user/settings">
                <ArrowLeft aria-hidden="true" />
                {t('chat.locked.action')}
              </Link>
            </Button>
          </CardContent>
        </Card>
      </section>
    )
  }
  return (
    <ChatConversation
      key={`${user.id}:${conversationId}`}
      conversationId={conversationId}
      userId={user.id}
    />
  )
}

export { CurrentBuddyRoutePage }
