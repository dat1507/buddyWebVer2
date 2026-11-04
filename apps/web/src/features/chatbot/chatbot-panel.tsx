import { useEffect, useRef, useSyncExternalStore, type KeyboardEvent } from 'react'
import { createPortal } from 'react-dom'
import {
  ArrowUpRight,
  BookOpen,
  ExternalLink,
  LoaderCircle,
  MessageCircle,
  RotateCcw,
  Send,
  X,
} from 'lucide-react'
import { useTranslation } from 'react-i18next'

import { Button } from '@/components/ui/button'
import { useModalIsolation } from '@/hooks/use-modal-isolation'
import { codePoints, validQuestion } from './chatbot-client'
import type { useChatbotConversation } from './use-chatbot-conversation'
import type { ApiError } from '@/lib/api'

const mediaQuery = '(max-width: 639px)'
function subscribeMobile(update: () => void) {
  const media = window.matchMedia(mediaQuery)
  media.addEventListener('change', update)
  return () => media.removeEventListener('change', update)
}
const mobileSnapshot = () => window.matchMedia(mediaQuery).matches

function errorKey(error: ApiError) {
  if (error.status === 429) return 'rateLimited'
  if ([400, 413, 415, 422].includes(error.status)) return 'validation'
  if (error.status === 503 || error.status === 404) return 'unavailable'
  if (error.status === 504 || error.code === 'timeout') return 'timeout'
  if (error.code === 'network') return 'network'
  if (error.code === 'cancelled') return 'cancelled'
  if (error.code === 'invalidResponse') return 'invalidResponse'
  return 'server'
}

interface Props {
  id: string
  open: boolean
  conversation: ReturnType<typeof useChatbotConversation>
  onClose: () => void
  onReady: () => void
  onExited: () => void
}

function ChatbotPanel({ id, open, conversation: chat, onClose, onReady, onExited }: Props) {
  const { t } = useTranslation()
  const mobile = useSyncExternalStore(subscribeMobile, mobileSnapshot)
  const container = useRef<HTMLDivElement>(null)
  const panel = useRef<HTMLElement>(null)
  const input = useRef<HTMLTextAreaElement>(null)
  const messages = useRef<HTMLDivElement>(null)
  useModalIsolation(container, mobile && open)
  const count = codePoints(chat.draft)
  const invalid =
    chat.draft.length > 0 && !validQuestion(chat.draft) && chat.draft.trim().length > 0
  const last = chat.turns.at(-1)

  useEffect(() => {
    onReady()
  }, [onReady])
  useEffect(() => {
    if (open) {
      input.current?.focus({ preventScroll: true })
      return
    }
    // animationend is primary; computed duration bounds cleanup if the event is lost.
    // Zero duration (including reduced motion) unmounts on the next task.
    const node = panel.current
    const style = node ? getComputedStyle(node) : null
    const duration = (value: string) =>
      value.split(',').reduce((max, part) => {
        const time = parseFloat(part) || 0
        return Math.max(max, part.trim().endsWith('ms') ? time : time * 1000)
      }, 0)
    const milliseconds = style
      ? duration(style.animationDuration) + duration(style.animationDelay)
      : 0
    const timer = window.setTimeout(onExited, milliseconds ? milliseconds + 50 : 0)
    function finish(event: AnimationEvent) {
      if (event.target === node && event.animationName === 'chatbot-exit') onExited()
    }
    node?.addEventListener('animationend', finish)
    return () => {
      window.clearTimeout(timer)
      node?.removeEventListener('animationend', finish)
    }
  }, [open, onExited])
  useEffect(() => {
    if (!mobile || !open) return
    const previous = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    return () => {
      document.body.style.overflow = previous
    }
  }, [mobile, open])
  useEffect(() => {
    const viewport = window.visualViewport
    function resize() {
      container.current?.style.setProperty(
        '--chatbot-vh',
        `${viewport?.height ?? window.innerHeight}px`,
      )
      container.current?.style.setProperty('--chatbot-top', `${viewport?.offsetTop ?? 0}px`)
    }
    resize()
    viewport?.addEventListener('resize', resize)
    viewport?.addEventListener('scroll', resize)
    return () => {
      viewport?.removeEventListener('resize', resize)
      viewport?.removeEventListener('scroll', resize)
    }
  }, [])
  useEffect(() => {
    // Scroll the chat area only; never scroll the surrounding page or move keyboard focus.
    const area = messages.current
    if (area) area.scrollTop = area.scrollHeight
  }, [chat.turns])

  function keydown(event: KeyboardEvent<HTMLElement>) {
    if (event.key === 'Escape' && !event.nativeEvent.isComposing) {
      event.preventDefault()
      event.stopPropagation()
      onClose()
      return
    }
    if (!mobile || event.key !== 'Tab' || !panel.current) return
    const nodes = [...panel.current.querySelectorAll<HTMLElement>('*')].filter(
      (element) => element.tabIndex >= 0 && !element.hasAttribute('disabled') && !element.hidden,
    )
    const first = nodes[0],
      lastNode = nodes.at(-1)
    if (event.shiftKey && document.activeElement === first) {
      event.preventDefault()
      lastNode?.focus({ preventScroll: true })
    } else if (!event.shiftKey && document.activeElement === lastNode) {
      event.preventDefault()
      first?.focus({ preventScroll: true })
    }
  }

  return createPortal(
    <div
      ref={container}
      className="chatbot-container"
      data-state={open ? 'open' : 'closing'}
      inert={!open}
      aria-hidden={!open || undefined}
    >
      <section
        ref={panel}
        id={id}
        className="chatbot-panel"
        role={mobile ? 'dialog' : 'region'}
        aria-modal={mobile && open ? true : undefined}
        aria-labelledby={`${id}-title`}
        aria-describedby={`${id}-scope`}
        onKeyDown={keydown}
      >
        <header className="chatbot-header">
          <span className="chatbot-avatar">
            <MessageCircle aria-hidden="true" size={22} />
          </span>
          <div className="min-w-0 flex-1">
            <h2 id={`${id}-title`}>{t('chatbot.title')}</h2>
            <p>{t('chatbot.subtitle')}</p>
          </div>
          <Button
            type="button"
            size="icon"
            variant="ghost"
            title={t('chatbot.clear')}
            aria-label={t('chatbot.clear')}
            onClick={chat.clear}
          >
            <RotateCcw aria-hidden="true" />
          </Button>
          <Button
            type="button"
            size="icon"
            variant="ghost"
            title={t('chatbot.close')}
            aria-label={t('chatbot.close')}
            onClick={onClose}
          >
            <X aria-hidden="true" />
          </Button>
        </header>
        <div
          className="chatbot-messages"
          ref={messages}
          role="log"
          tabIndex={0}
          aria-label={t('chatbot.messages')}
          aria-live={open ? 'polite' : 'off'}
          aria-relevant="additions text"
        >
          <div className="chatbot-welcome" data-empty={chat.turns.length === 0}>
            <span className="chatbot-eyebrow">{t('chatbot.welcomeLabel')}</span>
            {chat.turns.length === 0 ? (
              <>
                <h3>{t('chatbot.welcomeTitle')}</h3>
                <p>{t('chatbot.welcome')}</p>
                <div
                  className="chatbot-suggestions"
                  role="group"
                  aria-label={t('chatbot.suggestions')}
                >
                  {(['register', 'matching'] as const).map((topic) => (
                    <Button
                      key={topic}
                      type="button"
                      variant="secondary"
                      disabled={chat.pending || chat.retrySeconds > 0}
                      onClick={() => {
                        input.current?.focus({ preventScroll: true })
                        void chat.send(t(`chatbot.suggested.${topic}.question`))
                      }}
                    >
                      {t(`chatbot.suggested.${topic}.label`)}
                      <ArrowUpRight size={16} aria-hidden="true" />
                    </Button>
                  ))}
                </div>
              </>
            ) : null}
            <p className="chatbot-scope" id={`${id}-scope`}>
              {t('chatbot.scope')}
            </p>
          </div>
          {chat.turns.map((turn) => (
            <div className="chatbot-turn" key={turn.id}>
              <div className="chatbot-question">
                <span className="sr-only">{t('chatbot.you')}: </span>
                {turn.question}
              </div>
              {turn.status === 'pending' ? (
                <p className="chatbot-pending" role="status">
                  <LoaderCircle className="motion-safe:animate-spin" size={16} aria-hidden="true" />
                  {t('chatbot.loading')}
                </p>
              ) : null}
              {turn.reply ? (
                <div
                  className="chatbot-answer"
                  lang={turn.reply.language === 'und' ? undefined : turn.reply.language}
                >
                  <span className="sr-only">{t('chatbot.title')}: </span>
                  {turn.reply.status === 'historical_reference' ? (
                    <span className="chatbot-historical">{t('chatbot.historical')}</span>
                  ) : null}
                  {turn.reply.status === 'owner_provided' || turn.reply.status === 'conflicted' ? (
                    <span className="chatbot-historical">
                      {t(
                        turn.reply.status === 'conflicted'
                          ? 'chatbot.conflicted'
                          : 'chatbot.ownerProvided',
                      )}
                    </span>
                  ) : null}
                  <p>{turn.reply.answer}</p>
                  {turn.reply.sources.length ? (
                    <details className="chatbot-sources">
                      <summary>
                        <BookOpen size={14} aria-hidden="true" />
                        {t('chatbot.sources', { count: turn.reply.sources.length })}
                      </summary>
                      <ul>
                        {turn.reply.sources.map((source) => (
                          <li key={source.entry_id}>
                            <span>
                              {source.title === 'BuddyWeb guide'
                                ? t('chatbot.guide')
                                : source.verification_status === 'historical_reference'
                                  ? t('chatbot.historicalGuide')
                                  : ['owner_provided', 'conflicted'].includes(
                                        source.verification_status,
                                      )
                                    ? t('chatbot.ownerGuide')
                                    : t('chatbot.publicInfo')}
                            </span>
                            <span className="chatbot-source-id">
                              {source.entry_id} ·{' '}
                              {['historical_reference', 'owner_provided', 'conflicted'].includes(
                                source.verification_status,
                              )
                                ? t('chatbot.notVerified')
                                : t('chatbot.verified', { date: source.verified_on })}
                            </span>
                            {source.provenance ? (
                              <span className="chatbot-source-id">
                                {t('chatbot.sourceLines', {
                                  start: source.provenance.start_line,
                                  end: source.provenance.end_line,
                                })}{' '}
                                ·{' '}
                                {t('chatbot.sourceVersion', {
                                  version: source.provenance.sha256.slice(0, 12),
                                })}
                              </span>
                            ) : null}
                            {source.references.map((ref) => (
                              <a
                                key={ref.url}
                                href={ref.url}
                                target="_blank"
                                rel="noopener noreferrer"
                                referrerPolicy="no-referrer"
                              >
                                {ref.title}
                                <ExternalLink size={12} aria-hidden="true" />
                                <span className="sr-only">{t('chatbot.newTab')}</span>
                              </a>
                            ))}
                          </li>
                        ))}
                      </ul>
                    </details>
                  ) : null}
                </div>
              ) : null}
              {turn.error ? (
                <div className="chatbot-error">
                  <p role="status">{t(`chatbot.errors.${errorKey(turn.error)}`)}</p>
                  {last?.id === turn.id ? (
                    <Button
                      type="button"
                      variant="secondary"
                      size="sm"
                      disabled={chat.pending || chat.retrySeconds > 0}
                      onClick={() => void chat.send(turn.question, turn.id)}
                    >
                      {t('chatbot.retry')}
                    </Button>
                  ) : null}
                </div>
              ) : null}
            </div>
          ))}
        </div>
        <form
          className="chatbot-composer"
          onSubmit={(event) => {
            event.preventDefault()
            input.current?.focus({ preventScroll: true })
            void chat.send(chat.draft.trim())
          }}
        >
          {chat.retrySeconds > 0 ? (
            <p className="chatbot-notice">{t('chatbot.wait', { seconds: chat.retrySeconds })}</p>
          ) : null}
          <label htmlFor={`${id}-input`} className="sr-only">
            {t('chatbot.inputLabel')}
          </label>
          <div className="chatbot-input-row">
            <textarea
              id={`${id}-input`}
              ref={input}
              rows={2}
              maxLength={1000}
              value={chat.draft}
              placeholder={t('chatbot.placeholder')}
              aria-invalid={invalid || undefined}
              aria-describedby={`${id}-hint`}
              onChange={(event) => chat.setDraft(event.target.value)}
              onKeyDown={(event) => {
                if (
                  event.key === 'Enter' &&
                  !event.shiftKey &&
                  !event.nativeEvent.isComposing &&
                  event.keyCode !== 229
                ) {
                  event.preventDefault()
                  void chat.send(chat.draft.trim())
                }
              }}
            />
            <Button
              type="submit"
              size="icon"
              variant="secondary"
              aria-label={t('chatbot.send')}
              disabled={chat.pending || chat.retrySeconds > 0 || !validQuestion(chat.draft)}
            >
              {chat.pending ? (
                <LoaderCircle className="motion-safe:animate-spin" aria-hidden="true" />
              ) : (
                <Send aria-hidden="true" />
              )}
            </Button>
          </div>
          <div id={`${id}-hint`} className="chatbot-hint">
            <span>{invalid ? t('chatbot.errors.validation') : t('chatbot.hint')}</span>
            {count >= 400 ? <span>{count}/500</span> : null}
          </div>
        </form>
      </section>
    </div>,
    document.body,
  )
}

export default ChatbotPanel
