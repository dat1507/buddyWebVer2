import { useCallback, useEffect, useId, useRef, type ReactNode } from 'react'
import { createPortal } from 'react-dom'
import { LoaderCircle } from 'lucide-react'

import { Button } from '@/components/ui/button'
import { useModalIsolation } from '@/hooks/use-modal-isolation'

interface ConfirmDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  onConfirm: () => void
  title: ReactNode
  description: ReactNode
  confirmLabel: string
  cancelLabel: string
  destructive?: boolean
  confirmDisabled?: boolean
  isPending?: boolean
  pendingLabel?: string
  error?: ReactNode
}

interface ConfirmDialogContentProps extends Omit<ConfirmDialogProps, 'open' | 'onOpenChange'> {
  onClose: () => void
}

const focusableSelector = [
  'a[href]',
  'button:not([disabled])',
  'input:not([disabled])',
  'select:not([disabled])',
  'textarea:not([disabled])',
  '[tabindex]:not([tabindex="-1"])',
].join(', ')

function ConfirmDialogContent({
  onClose,
  onConfirm,
  title,
  description,
  confirmLabel,
  cancelLabel,
  destructive = false,
  confirmDisabled = false,
  isPending = false,
  pendingLabel,
  error,
}: ConfirmDialogContentProps) {
  const id = useId()
  const backdropRef = useRef<HTMLDivElement>(null)
  const dialogRef = useRef<HTMLDivElement>(null)
  const cancelButtonRef = useRef<HTMLButtonElement>(null)
  const isPendingRef = useRef(isPending)
  const onCloseRef = useRef(onClose)

  useModalIsolation(backdropRef)

  useEffect(() => {
    isPendingRef.current = isPending
  }, [isPending])

  useEffect(() => {
    onCloseRef.current = onClose
  }, [onClose])

  useEffect(() => {
    if (!isPending || !dialogRef.current) return

    const activeElement = document.activeElement
    const activeControlWasDisabled =
      activeElement instanceof HTMLButtonElement && activeElement.disabled

    if (!dialogRef.current.contains(activeElement) || activeControlWasDisabled) {
      dialogRef.current.focus()
    }
  }, [isPending])

  useEffect(() => {
    const previouslyFocusedElement =
      document.activeElement instanceof HTMLElement ? document.activeElement : null
    const previousOverflow = document.body.style.overflow

    document.body.style.overflow = 'hidden'
    if (cancelButtonRef.current && !cancelButtonRef.current.disabled) {
      cancelButtonRef.current.focus()
    } else {
      dialogRef.current?.focus()
    }

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        event.preventDefault()
        if (!isPendingRef.current) onCloseRef.current()
        return
      }

      if (event.key !== 'Tab' || !dialogRef.current) return

      const focusableElements = Array.from(
        dialogRef.current.querySelectorAll<HTMLElement>(focusableSelector),
      ).filter((element) => !element.hasAttribute('hidden') && element.tabIndex >= 0)

      if (focusableElements.length === 0) {
        event.preventDefault()
        dialogRef.current.focus()
        return
      }

      const firstElement = focusableElements[0]
      const lastElement = focusableElements[focusableElements.length - 1]
      const activeElement = document.activeElement

      if (!dialogRef.current.contains(activeElement)) {
        event.preventDefault()
        ;(event.shiftKey ? lastElement : firstElement).focus()
      } else if (event.shiftKey && activeElement === firstElement) {
        event.preventDefault()
        lastElement.focus()
      } else if (!event.shiftKey && activeElement === lastElement) {
        event.preventDefault()
        firstElement.focus()
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
  const errorId = error ? `${id}-error` : undefined
  const describedBy = errorId ? `${descriptionId} ${errorId}` : descriptionId

  return (
    <div
      ref={backdropRef}
      className="fixed inset-0 z-[100] flex items-center justify-center bg-black/65 p-4 backdrop-blur-sm"
      data-testid="confirm-dialog-backdrop"
      onClick={(event) => {
        if (event.target === event.currentTarget && !isPending) onClose()
      }}
    >
      <div
        ref={dialogRef}
        role="alertdialog"
        aria-modal="true"
        aria-labelledby={titleId}
        aria-describedby={describedBy}
        aria-busy={isPending}
        tabIndex={-1}
        className="w-full max-w-md rounded-2xl border border-border bg-card p-6 text-card-foreground shadow-2xl outline-none"
      >
        <h2 id={titleId} className="text-xl font-semibold leading-tight">
          {title}
        </h2>
        <div id={descriptionId} className="mt-2 text-sm leading-6 text-muted-foreground">
          {description}
        </div>

        {error ? (
          <div
            id={errorId}
            role="alert"
            className="mt-4 rounded-xl border border-destructive/40 bg-destructive/10 px-3 py-2 text-sm text-destructive"
          >
            {error}
          </div>
        ) : null}

        <div className="mt-6 flex flex-col-reverse gap-3 sm:flex-row sm:justify-end">
          <Button
            ref={cancelButtonRef}
            type="button"
            variant="secondary"
            disabled={isPending}
            onClick={onClose}
          >
            {cancelLabel}
          </Button>
          <Button
            type="button"
            variant={destructive ? 'destructive' : 'default'}
            disabled={confirmDisabled || isPending}
            aria-busy={isPending}
            onClick={onConfirm}
          >
            {isPending ? (
              <LoaderCircle
                aria-hidden="true"
                className="animate-spin motion-reduce:animate-none"
              />
            ) : null}
            {isPending && pendingLabel ? pendingLabel : confirmLabel}
          </Button>
        </div>
      </div>
    </div>
  )
}

function ConfirmDialog({ open, onOpenChange, ...contentProps }: ConfirmDialogProps) {
  const onOpenChangeRef = useRef(onOpenChange)
  const closeDialog = useCallback(() => onOpenChangeRef.current(false), [])

  useEffect(() => {
    onOpenChangeRef.current = onOpenChange
  }, [onOpenChange])

  if (!open || typeof document === 'undefined') return null

  return createPortal(
    <ConfirmDialogContent {...contentProps} onClose={closeDialog} />,
    document.body,
  )
}

export { ConfirmDialog }
export type { ConfirmDialogProps }
