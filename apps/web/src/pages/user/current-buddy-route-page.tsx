import { Link, Navigate, useLocation } from 'react-router'
import { ArrowLeft, LockKeyhole } from 'lucide-react'
import { useTranslation } from 'react-i18next'

import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { ChatConversation } from '@/features/chat/chat-conversation'
import {
  conversationIdFromBuddyLocation,
  currentBuddiesDestination,
} from '@/features/matching/current-buddy'
import { useAuthStore } from '@/stores/auth-store'

function CurrentBuddyRoutePage() {
  const { t } = useTranslation()
  const location = useLocation()
  const user = useAuthStore((state) => state.user)
  const conversationId = conversationIdFromBuddyLocation(location)
  if (!conversationId) return <Navigate to={currentBuddiesDestination(null)} replace />
  if (!user) return null
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
