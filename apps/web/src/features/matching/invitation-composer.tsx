import { useEffect, useId, useMemo, useRef, useState, type FormEvent } from 'react'
import { createPortal } from 'react-dom'
import { LoaderCircle, Send } from 'lucide-react'
import { useTranslation } from 'react-i18next'

import { Button } from '@/components/ui/button'
import {
  MAX_INVITATION_MESSAGE_CODE_POINTS,
  MAX_INVITATION_MESSAGE_WORDS,
  validateInvitationMessage,
} from '@/features/matching/invitation'
import type { MatchingProfile } from '@/features/matching/recommendation'
import { useModalIsolation } from '@/hooks/use-modal-isolation'

interface InvitationComposerProps {
  target: MatchingProfile | null
  pending: boolean
  errorKey: string | null
  onCancel: () => void
  onSubmit: (message: string) => Promise<void>
}

const focusableSelector = [
  'button:not([disabled])',
  'textarea:not([disabled])',
  '[tabindex]:not([tabindex="-1"])',
].join(', ')

function InvitationComposerContent({
  target,
  pending,
  errorKey,
  onCancel,
  onSubmit,
}: Omit<InvitationComposerProps, 'target'> & { target: MatchingProfile }) {
  const { t } = useTranslation()
  const id = useId()
  const backdropRef = useRef<HTMLDivElement>(null)
  const dialogRef = useRef<HTMLDivElement>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const pendingRef = useRef(pending)
  const onCancelRef = useRef(onCancel)
  const submitStartedRef = useRef(false)
  const [message, setMessage] = useState('')
  const validation = useMemo(() => validateInvitationMessage(message), [message])
  const name = target.display_name?.trim() || t('recommendedBuddies.unnamed')

  useModalIsolation(backdropRef)

  useEffect(() => {
    pendingRef.current = pending
    if (pending) dialogRef.current?.focus()
  }, [pending])

  useEffect(() => {
    onCancelRef.current = onCancel
  }, [onCancel])

  useEffect(() => {
    const previouslyFocusedElement =
      document.activeElement instanceof HTMLElement ? document.activeElement : null
    const previousOverflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    textareaRef.current?.focus()

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        event.preventDefault()
        if (!pendingRef.current) onCancelRef.current()
        return
      }
      if (event.key !== 'Tab' || !dialogRef.current) return
      const focusableElements = Array.from(
        dialogRef.current.querySelectorAll<HTMLElement>(focusableSelector),
      ).filter((element) => element.tabIndex >= 0)
      if (focusableElements.length === 0) {
        event.preventDefault()
        dialogRef.current.focus()
        return
      }
      const first = focusableElements[0]
      const last = focusableElements[focusableElements.length - 1]
      const active = document.activeElement
      if (!dialogRef.current.contains(active)) {
        event.preventDefault()
        ;(event.shiftKey ? last : first).focus()
      } else if (event.shiftKey && active === first) {
        event.preventDefault()
        last.focus()
      } else if (!event.shiftKey && active === last) {
        event.preventDefault()
        first.focus()
      }
    }
    document.addEventListener('keydown', handleKeyDown)
    return () => {
      document.body.style.overflow = previousOverflow
      document.removeEventListener('keydown', handleKeyDown)
      previouslyFocusedElement?.focus()
    }
  }, [])

  const titleId = `${id}-title`
  const descriptionId = `${id}-description`
  const helpId = `${id}-help`
  const counterId = `${id}-counter`
  const validationId = validation.reason ? `${id}-validation` : undefined
  const serverErrorId = errorKey ? `${id}-server-error` : undefined
  const describedBy = [helpId, counterId, validationId, serverErrorId].filter(Boolean).join(' ')

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    if (pending || validation.reason || submitStartedRef.current) return
    submitStartedRef.current = true
    try {
      await onSubmit(validation.canonical)
    } finally {
      submitStartedRef.current = false
    }
  }

  return (
    <div
      ref={backdropRef}
      className="fixed inset-0 z-[100] flex items-center justify-center overflow-y-auto bg-black/65 p-3 backdrop-blur-sm sm:p-6"
      data-testid="invitation-composer-backdrop"
      onClick={(event) => {
        if (event.target === event.currentTarget && !pending) onCancel()
      }}
    >
      <div
        ref={dialogRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        aria-describedby={descriptionId}
        aria-busy={pending}
        tabIndex={-1}
        className="my-auto max-h-[calc(100vh-1.5rem)] w-full max-w-2xl overflow-y-auto rounded-2xl border border-border bg-card p-5 text-card-foreground shadow-2xl outline-none sm:max-h-[calc(100vh-3rem)] sm:p-6"
      >
        <h2 id={titleId} className="break-words text-xl font-semibold leading-tight">
          {t('invitations.composer.title', { name })}
        </h2>
        <p id={descriptionId} className="mt-2 text-sm leading-6 text-muted-foreground">
          {t('invitations.composer.description')}
        </p>

        <div className="mt-4 rounded-xl border border-border bg-muted/35 p-4">
          <p className="break-words font-semibold">{name}</p>
          <p className="mt-1 break-words text-sm text-muted-foreground">
            {t(`recommendedBuddies.studentTypes.${target.student_type}`)} ·{' '}
            {target.major?.trim() || t('recommendedBuddies.majorNotShared')}
          </p>
        </div>

        <form className="mt-5 space-y-4" onSubmit={(event) => void submit(event)}>
          <div>
            <label className="text-sm font-semibold" htmlFor={`${id}-message`}>
              {t('invitations.composer.messageLabel')}
            </label>
            <p id={helpId} className="mt-1 text-sm text-muted-foreground">
              {t('invitations.composer.messageHelp')}
            </p>
            <textarea
              ref={textareaRef}
              id={`${id}-message`}
              rows={8}
              value={message}
              disabled={pending}
              aria-invalid={Boolean(validation.reason)}
              aria-describedby={describedBy}
              className="mt-3 min-h-40 w-full resize-y rounded-xl border border-input bg-background px-3 py-2 text-sm shadow-sm outline-none focus-visible:ring-2 focus-visible:ring-vgu-orange disabled:cursor-not-allowed disabled:opacity-60"
              onChange={(event) => setMessage(event.currentTarget.value)}
            />
            <div
              id={counterId}
              className="mt-2 flex flex-wrap justify-between gap-2 text-xs text-muted-foreground"
              aria-live="polite"
            >
              <span>
                {t('invitations.composer.wordCount', {
                  count: validation.wordCount,
                  limit: MAX_INVITATION_MESSAGE_WORDS,
                })}
              </span>
              <span>
                {t('invitations.composer.codePointCount', {
                  count: validation.codePointCount,
                  limit: MAX_INVITATION_MESSAGE_CODE_POINTS,
                })}
              </span>
            </div>
            {validation.reason ? (
              <p id={validationId} role="alert" className="mt-2 text-sm text-destructive">
                {t(
                  validation.reason === 'INVITATION_MESSAGE_TOO_MANY_WORDS'
                    ? 'invitations.errors.messageTooManyWords'
                    : 'invitations.errors.messageTooManyCodePoints',
                )}
              </p>
            ) : null}
          </div>

          {errorKey ? (
            <p
              id={serverErrorId}
              role="alert"
              className="rounded-xl border border-destructive/40 bg-destructive/10 px-3 py-2 text-sm text-destructive"
            >
              {t(`invitations.errors.${errorKey}`)}
            </p>
          ) : null}

          <div className="flex flex-col-reverse gap-3 sm:flex-row sm:justify-end">
            <Button type="button" variant="secondary" disabled={pending} onClick={onCancel}>
              {t('invitations.composer.cancel')}
            </Button>
            <Button type="submit" disabled={pending || Boolean(validation.reason)}>
              {pending ? (
                <LoaderCircle
                  aria-hidden="true"
                  className="animate-spin motion-reduce:animate-none"
                />
              ) : (
                <Send aria-hidden="true" />
              )}
              {pending ? t('invitations.composer.sending') : t('invitations.composer.submit')}
            </Button>
          </div>
        </form>
      </div>
    </div>
  )
}

function InvitationComposer({ target, ...props }: InvitationComposerProps) {
  if (!target || typeof document === 'undefined') return null
  return createPortal(
    <InvitationComposerContent key={target.id} target={target} {...props} />,
    document.body,
  )
}

export { InvitationComposer }
export type { InvitationComposerProps }
