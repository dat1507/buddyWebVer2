import { useEffect, useId, useRef, useState } from 'react'
import {
  ArrowDown,
  ArrowLeft,
  CircleAlert,
  LoaderCircle,
  RefreshCw,
  Send,
  Wifi,
  WifiOff,
} from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { Link } from 'react-router'

import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Typography } from '@/components/ui/typography'
import { CHAT_MESSAGE_MAX_CODE_POINTS, countChatCodePoints } from '@/features/chat/chat'
import type { ChatMessage } from '@/features/chat/chat'
import type { PendingChatMessage } from '@/features/chat/use-chat-conversation'
import { useChatConversation } from '@/features/chat/use-chat-conversation'
import { cn } from '@/lib/utils'

function formatMessageTime(value: string, locale: string): string {
  return new Intl.DateTimeFormat(locale, {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(new Date(value))
}

function PersistedMessage({ message, locale }: { message: ChatMessage; locale: string }) {
  const { t } = useTranslation()
  const own = message.sender === 'self'
  return (
    <li
      className={cn('flex min-w-0', own ? 'justify-end' : 'justify-start')}
      aria-label={t(own ? 'chat.message.fromSelf' : 'chat.message.fromBuddy')}
    >
      <article
        className={cn(
          'max-w-[92%] rounded-2xl border px-4 py-3 shadow-sm sm:max-w-[78%]',
          own
            ? 'rounded-br-md border-vgu-orange/40 bg-vgu-orange/10'
            : 'rounded-bl-md border-border bg-card',
        )}
      >
        <p className="mb-1 text-xs font-semibold text-muted-foreground">
          {t(own ? 'chat.message.you' : 'chat.message.buddy')}
        </p>
        <p className="whitespace-pre-wrap break-words [overflow-wrap:anywhere]">{message.body}</p>
        <time dateTime={message.created_at} className="mt-2 block text-xs text-muted-foreground">
          {formatMessageTime(message.created_at, locale)}
        </time>
      </article>
    </li>
  )
}

function PendingMessage({ message, retry }: { message: PendingChatMessage; retry: () => void }) {
  const { t } = useTranslation()
  return (
    <li className="flex min-w-0 justify-end" aria-label={t('chat.message.fromSelf')}>
      <article className="max-w-[92%] rounded-2xl rounded-br-md border border-dashed border-vgu-orange/50 bg-vgu-orange/5 px-4 py-3 sm:max-w-[78%]">
        <p className="mb-1 text-xs font-semibold text-muted-foreground">{t('chat.message.you')}</p>
        <p className="whitespace-pre-wrap break-words [overflow-wrap:anywhere]">{message.body}</p>
        {message.status === 'sending' || message.status === 'confirmed' ? (
          <p className="mt-2 flex items-center gap-2 text-xs text-muted-foreground" role="status">
            {message.status === 'sending' ? (
              <LoaderCircle
                aria-hidden="true"
                className="size-3.5 animate-spin motion-reduce:animate-none"
              />
            ) : (
              <RefreshCw aria-hidden="true" className="size-3.5" />
            )}
            {t(
              message.status === 'sending' ? 'chat.message.sending' : 'chat.message.synchronizing',
            )}
          </p>
        ) : (
          <div className="mt-2 flex flex-wrap items-center gap-2 text-xs text-destructive">
            <span role="alert">{t('chat.message.failed')}</span>
            <Button type="button" variant="outline" size="sm" onClick={retry}>
              <RefreshCw aria-hidden="true" />
              {t('chat.message.retry')}
            </Button>
          </div>
        )}
      </article>
    </li>
  )
}

function ChatConversation({ conversationId, userId }: { conversationId: string; userId: string }) {
  const { t, i18n } = useTranslation()
  const titleId = useId()
  const composerId = useId()
  const composerHelpId = useId()
  const composerErrorId = useId()
  const scrollRef = useRef<HTMLDivElement>(null)
  const nearBottomRef = useRef(true)
  const previousVisibleCountRef = useRef(0)
  const [body, setBody] = useState('')
  const [submitted, setSubmitted] = useState(false)
  const [newMessagesAvailable, setNewMessagesAvailable] = useState(false)
  const chat = useChatConversation({ conversationId, userId })
  const locale = i18n.resolvedLanguage ?? 'en'
  const codePointCount = countChatCodePoints(body)
  const blank = body.trim().length === 0
  const tooLong = codePointCount > CHAT_MESSAGE_MAX_CODE_POINTS
  const validationKey =
    body.length > 0 && blank
      ? 'chat.composer.blank'
      : tooLong
        ? 'chat.composer.tooLong'
        : submitted && blank
          ? 'chat.composer.blank'
          : null
  const visibleCount = chat.messages.length + chat.pendingMessages.length

  const scrollToBottom = (behavior: ScrollBehavior = 'smooth') => {
    const container = scrollRef.current
    if (!container) return
    container.scrollTo?.({ top: container.scrollHeight, behavior })
    nearBottomRef.current = true
    setNewMessagesAvailable(false)
  }

  useEffect(() => {
    if (visibleCount <= previousVisibleCountRef.current) {
      previousVisibleCountRef.current = visibleCount
      return
    }
    if (nearBottomRef.current)
      scrollToBottom(previousVisibleCountRef.current === 0 ? 'auto' : 'smooth')
    else setNewMessagesAvailable(true)
    previousVisibleCountRef.current = visibleCount
  }, [visibleCount])

  const loadOlder = async () => {
    const container = scrollRef.current
    const previousHeight = container?.scrollHeight ?? 0
    const previousTop = container?.scrollTop ?? 0
    await chat.loadOlder()
    requestAnimationFrame(() => {
      if (!container) return
      container.scrollTop = previousTop + (container.scrollHeight - previousHeight)
    })
  }

  const submit = () => {
    setSubmitted(true)
    if (blank || tooLong || chat.isSending) return
    if (chat.sendMessage(body)) {
      setBody('')
      setSubmitted(false)
    }
  }

  const connectionLabel = t(`chat.connection.${chat.connectionState}`)
  const connectionUnavailable = ['offline', 'reconnecting'].includes(chat.connectionState)

  if (chat.accessDenied) {
    return (
      <section aria-labelledby={titleId} className="min-w-0 py-6">
        <Card className="mx-auto max-w-2xl border-amber-500/40">
          <CardHeader>
            <CircleAlert aria-hidden="true" className="size-6 text-amber-600" />
            <CardTitle id={titleId}>{t('chat.unavailable.title')}</CardTitle>
            <CardDescription role="alert">{t('chat.unavailable.description')}</CardDescription>
          </CardHeader>
          <CardContent>
            <Button asChild variant="outline">
              <Link to="/user/matching#current-buddies">
                <ArrowLeft aria-hidden="true" />
                {t('chat.backToBuddies')}
              </Link>
            </Button>
          </CardContent>
        </Card>
      </section>
    )
  }

  if (chat.isLoadingHistory) {
    return (
      <div className="flex min-h-64 items-center justify-center gap-3 text-muted-foreground">
        <LoaderCircle
          aria-hidden="true"
          className="size-5 animate-spin motion-reduce:animate-none"
        />
        <span role="status">{t('chat.loading')}</span>
      </div>
    )
  }

  if (chat.isHistoryError && chat.messages.length === 0) {
    return (
      <section aria-labelledby={titleId} className="min-w-0 py-6">
        <Card className="mx-auto max-w-2xl border-destructive/40">
          <CardHeader>
            <CircleAlert aria-hidden="true" className="size-6 text-destructive" />
            <CardTitle id={titleId}>{t('chat.loadError.title')}</CardTitle>
            <CardDescription role="alert">{t('chat.loadError.description')}</CardDescription>
          </CardHeader>
          <CardContent className="flex flex-wrap gap-3">
            <Button type="button" onClick={() => void chat.refetchHistory()}>
              {t('chat.loadError.retry')}
            </Button>
            <Button asChild variant="outline">
              <Link to="/user/matching#current-buddies">{t('chat.backToBuddies')}</Link>
            </Button>
          </CardContent>
        </Card>
      </section>
    )
  }

  return (
    <section aria-labelledby={titleId} className="min-w-0 space-y-4 py-4 sm:py-6">
      <header className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <Button asChild variant="outline" size="sm" className="mb-3">
            <Link to="/user/matching#current-buddies">
              <ArrowLeft aria-hidden="true" />
              {t('chat.backToBuddies')}
            </Link>
          </Button>
          <Typography as="h1" variant="h2" id={titleId} className="break-words">
            {t('chat.title')}
          </Typography>
          <Typography variant="muted" className="mt-1">
            {t('chat.subtitle')}
          </Typography>
        </div>
        <div
          role="status"
          aria-live="polite"
          className={cn(
            'flex items-center gap-2 rounded-full border px-3 py-2 text-sm',
            chat.connectionState === 'connected'
              ? 'border-emerald-500/30 text-emerald-700 dark:text-emerald-300'
              : 'border-amber-500/40 text-amber-700 dark:text-amber-300',
          )}
        >
          {chat.connectionState === 'connected' ? (
            <Wifi aria-hidden="true" className="size-4" />
          ) : (
            <WifiOff aria-hidden="true" className="size-4" />
          )}
          {connectionLabel}
        </div>
      </header>

      {connectionUnavailable ? (
        <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-amber-500/40 bg-amber-500/10 p-3 text-sm">
          <p>{t('chat.connection.fallback')}</p>
          {chat.connectionState === 'offline' ? (
            <Button type="button" variant="outline" size="sm" onClick={chat.retryConnection}>
              <RefreshCw aria-hidden="true" />
              {t('chat.connection.retry')}
            </Button>
          ) : null}
        </div>
      ) : null}

      <Card className="min-w-0 overflow-hidden">
        <CardContent className="p-0">
          <div className="border-b border-border p-3 text-center">
            {chat.hasOlder ? (
              <Button
                type="button"
                variant="outline"
                size="sm"
                disabled={chat.isLoadingOlder}
                onClick={() => void loadOlder()}
              >
                {chat.isLoadingOlder ? (
                  <LoaderCircle
                    aria-hidden="true"
                    className="animate-spin motion-reduce:animate-none"
                  />
                ) : (
                  <ArrowDown aria-hidden="true" className="rotate-180" />
                )}
                {chat.isLoadingOlder ? t('chat.loadingOlder') : t('chat.loadOlder')}
              </Button>
            ) : chat.messages.length > 0 ? (
              <p className="text-xs text-muted-foreground">{t('chat.startOfHistory')}</p>
            ) : null}
            {chat.isRefreshingHistory ? (
              <span className="sr-only" role="status">
                {t('chat.refreshing')}
              </span>
            ) : null}
          </div>

          <div
            ref={scrollRef}
            className="relative max-h-[min(58vh,42rem)] min-h-72 overflow-y-auto overflow-x-hidden overscroll-contain p-3 sm:p-5"
            onScroll={(event) => {
              const target = event.currentTarget
              const nearBottom = target.scrollHeight - target.scrollTop - target.clientHeight < 96
              nearBottomRef.current = nearBottom
              if (nearBottom) setNewMessagesAvailable(false)
            }}
          >
            {chat.messages.length === 0 && chat.pendingMessages.length === 0 ? (
              <div className="flex min-h-56 items-center justify-center text-center text-muted-foreground">
                <p>{t('chat.empty')}</p>
              </div>
            ) : (
              <ol
                role="log"
                aria-label={t('chat.messageLog')}
                aria-live="polite"
                aria-relevant="additions"
                className="space-y-3"
              >
                {chat.messages.map((message) => (
                  <PersistedMessage key={message.id} message={message} locale={locale} />
                ))}
                {chat.pendingMessages.map((message) => (
                  <PendingMessage
                    key={message.clientMessageId}
                    message={message}
                    retry={() => chat.retryMessage(message.clientMessageId)}
                  />
                ))}
              </ol>
            )}
          </div>

          {newMessagesAvailable ? (
            <div className="border-t border-border p-2 text-center">
              <Button type="button" variant="outline" size="sm" onClick={() => scrollToBottom()}>
                <ArrowDown aria-hidden="true" />
                {t('chat.newMessages')}
              </Button>
            </div>
          ) : null}

          <form
            className="space-y-3 border-t border-border bg-muted/20 p-3 sm:p-5"
            onSubmit={(event) => {
              event.preventDefault()
              submit()
            }}
          >
            <label htmlFor={composerId} className="block text-sm font-semibold">
              {t('chat.composer.label')}
            </label>
            <textarea
              id={composerId}
              value={body}
              rows={3}
              aria-describedby={`${composerHelpId}${validationKey ? ` ${composerErrorId}` : ''}`}
              aria-invalid={validationKey ? true : undefined}
              className="w-full resize-y rounded-xl border border-input bg-background px-3 py-2 text-foreground shadow-sm outline-none focus-visible:ring-2 focus-visible:ring-vgu-orange"
              placeholder={t('chat.composer.placeholder')}
              onChange={(event) => {
                setBody(event.target.value)
                setSubmitted(false)
              }}
              onKeyDown={(event) => {
                if (event.key === 'Enter' && (event.ctrlKey || event.metaKey)) {
                  event.preventDefault()
                  submit()
                }
              }}
            />
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div className="space-y-1 text-xs text-muted-foreground">
                <p id={composerHelpId}>{t('chat.composer.help')}</p>
                <p aria-live="polite">
                  {t('chat.composer.count', {
                    count: codePointCount,
                    limit: CHAT_MESSAGE_MAX_CODE_POINTS,
                  })}
                </p>
                {validationKey ? (
                  <p id={composerErrorId} role="alert" className="text-destructive">
                    {t(validationKey)}
                  </p>
                ) : null}
              </div>
              <Button type="submit" disabled={chat.isSending || body.length === 0}>
                {chat.isSending ? (
                  <LoaderCircle
                    aria-hidden="true"
                    className="animate-spin motion-reduce:animate-none"
                  />
                ) : (
                  <Send aria-hidden="true" />
                )}
                {chat.isSending ? t('chat.composer.sending') : t('chat.composer.send')}
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>
    </section>
  )
}

export { ChatConversation }
