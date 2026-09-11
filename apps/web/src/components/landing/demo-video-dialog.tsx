import { useCallback, useEffect, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import { CircleAlert, LoaderCircle, X } from 'lucide-react'
import { useTranslation } from 'react-i18next'

import { Button } from '@/components/ui/button'
import { useModalIsolation } from '@/hooks/use-modal-isolation'

const demoVideoPath = '/media/vgu-buddy-demo.mp4'
const demoPosterPath = '/media/vgu-buddy-demo-poster.webp'

interface DemoVideoDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
}

interface DemoVideoDialogContentProps {
  onClose: () => void
}

function resetVideo(video: HTMLVideoElement | null) {
  if (!video) return

  video.pause()
  video.currentTime = 0
}

function DemoVideoDialogContent({ onClose }: DemoVideoDialogContentProps) {
  const { t } = useTranslation()
  const backdropRef = useRef<HTMLDivElement>(null)
  const dialogRef = useRef<HTMLDivElement>(null)
  const closeButtonRef = useRef<HTMLButtonElement>(null)
  const videoRef = useRef<HTMLVideoElement>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [hasError, setHasError] = useState(false)

  useModalIsolation(backdropRef)

  useEffect(() => {
    const previouslyFocusedElement =
      document.activeElement instanceof HTMLElement ? document.activeElement : null
    const previousOverflow = document.body.style.overflow
    const video = videoRef.current

    document.body.style.overflow = 'hidden'
    closeButtonRef.current?.focus()

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        event.preventDefault()
        onClose()
        return
      }

      if (event.key !== 'Tab' || !dialogRef.current) return

      const focusableElements = Array.from(
        dialogRef.current.querySelectorAll<HTMLElement>(
          'a[href], button:not([disabled]), video[controls], [tabindex]:not([tabindex="-1"])',
        ),
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
        const elementToFocus = event.shiftKey ? lastElement : firstElement
        elementToFocus.focus()
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
      resetVideo(video)
      document.body.style.overflow = previousOverflow
      document.removeEventListener('keydown', handleKeyDown)
      previouslyFocusedElement?.focus()
    }
  }, [onClose])

  return (
    <div
      ref={backdropRef}
      className="fixed inset-0 z-[100] flex items-center justify-center bg-black/80 p-3 backdrop-blur-sm sm:p-6"
      data-testid="demo-video-backdrop"
      onClick={(event) => {
        if (event.target === event.currentTarget) onClose()
      }}
    >
      <div
        ref={dialogRef}
        id="demo-video-dialog"
        role="dialog"
        aria-modal="true"
        aria-labelledby="demo-video-title"
        aria-describedby="demo-video-description"
        tabIndex={-1}
        className="flex max-h-[94dvh] w-full max-w-3xl flex-col overflow-hidden rounded-2xl border border-white/15 bg-zinc-950 shadow-2xl"
      >
        <div className="flex items-start justify-between gap-4 border-b border-white/10 px-4 py-3 sm:px-6 sm:py-4">
          <div className="min-w-0">
            <h2 id="demo-video-title" className="text-lg font-semibold text-white sm:text-xl">
              {t('demoDialog.title')}
            </h2>
            <p id="demo-video-description" className="mt-1 text-sm text-zinc-400">
              {t('demoDialog.description')}
            </p>
          </div>

          <Button
            ref={closeButtonRef}
            type="button"
            variant="ghost"
            size="icon"
            className="shrink-0 text-zinc-200 hover:bg-white/10 hover:text-orange-400"
            aria-label={t('demoDialog.close')}
            onClick={onClose}
          >
            <X aria-hidden="true" className="size-5" />
          </Button>
        </div>

        <div className="relative flex min-h-0 flex-1 items-center justify-center bg-black">
          <video
            ref={videoRef}
            src={demoVideoPath}
            poster={demoPosterPath}
            controls
            playsInline
            preload="metadata"
            tabIndex={hasError ? -1 : 0}
            aria-hidden={hasError || undefined}
            className="max-h-[78dvh] w-full bg-black object-contain"
            aria-label={t('demoDialog.videoLabel')}
            onLoadStart={() => {
              setIsLoading(true)
              setHasError(false)
            }}
            onCanPlay={() => setIsLoading(false)}
            onError={() => {
              setIsLoading(false)
              setHasError(true)
              closeButtonRef.current?.focus()
            }}
          />

          {isLoading && !hasError ? (
            <div
              className="pointer-events-none absolute inset-0 flex items-center justify-center bg-black/55"
              role="status"
            >
              <span className="inline-flex items-center gap-3 rounded-full bg-black/75 px-4 py-2 text-sm text-zinc-100">
                <LoaderCircle
                  aria-hidden="true"
                  className="size-5 animate-spin motion-reduce:animate-none"
                />
                {t('demoDialog.loading')}
              </span>
            </div>
          ) : null}

          {hasError ? (
            <div
              className="absolute inset-0 flex flex-col items-center justify-center bg-zinc-950/95 p-6 text-center"
              role="alert"
            >
              <CircleAlert aria-hidden="true" className="size-10 text-orange-500" />
              <p className="mt-4 max-w-md text-base text-zinc-200">{t('demoDialog.error')}</p>
            </div>
          ) : null}
        </div>
      </div>
    </div>
  )
}

function DemoVideoDialog({ open, onOpenChange }: DemoVideoDialogProps) {
  const onOpenChangeRef = useRef(onOpenChange)
  const closeDialog = useCallback(() => onOpenChangeRef.current(false), [])

  useEffect(() => {
    onOpenChangeRef.current = onOpenChange
  }, [onOpenChange])

  if (!open || typeof document === 'undefined') return null

  return createPortal(<DemoVideoDialogContent onClose={closeDialog} />, document.body)
}

export { DemoVideoDialog }
export type { DemoVideoDialogProps }
