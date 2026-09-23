import {
  useCallback,
  useEffect,
  useId,
  useRef,
  useState,
  type KeyboardEvent as ReactKeyboardEvent,
  type PointerEvent as ReactPointerEvent,
} from 'react'
import { createPortal } from 'react-dom'
import { LoaderCircle, Move, ZoomIn } from 'lucide-react'
import { useTranslation } from 'react-i18next'

import { Button } from '@/components/ui/button'
import {
  avatarCropLayout,
  clampAvatarOffset,
  createCroppedAvatarFile,
  validateAvatarSourceDimensions,
  type AvatarOffset,
  type AvatarSourceError,
} from '@/features/profile/avatar-image'
import { useModalIsolation } from '@/hooks/use-modal-isolation'

interface AvatarCropSource {
  file: File
  url: string
}

interface AvatarCropDialogProps {
  open: boolean
  source: AvatarCropSource | null
  onCancel: () => void
  onApply: (file: File) => void
}

interface ImageDimensions {
  width: number
  height: number
}

interface DragState {
  pointerId: number
  startX: number
  startY: number
  offset: AvatarOffset
}

const focusableSelector = [
  'button:not([disabled])',
  'input:not([disabled])',
  '[tabindex]:not([tabindex="-1"])',
].join(', ')

function AvatarCropDialogContent({
  source,
  onCancel,
  onApply,
}: Omit<AvatarCropDialogProps, 'open'>) {
  const { t } = useTranslation()
  const id = useId()
  const backdropRef = useRef<HTMLDivElement>(null)
  const dialogRef = useRef<HTMLDivElement>(null)
  const cancelButtonRef = useRef<HTMLButtonElement>(null)
  const viewportRef = useRef<HTMLDivElement>(null)
  const imageRef = useRef<HTMLImageElement>(null)
  const dragRef = useRef<DragState | null>(null)
  const processingRef = useRef(false)
  const onCancelRef = useRef(onCancel)
  const [dimensions, setDimensions] = useState<ImageDimensions | null>(null)
  const [viewportSize, setViewportSize] = useState(256)
  const [zoom, setZoom] = useState(1)
  const [offset, setOffset] = useState<AvatarOffset>({ x: 0, y: 0 })
  const [error, setError] = useState<AvatarSourceError | null>(null)
  const [processing, setProcessing] = useState(false)

  useModalIsolation(backdropRef)

  useEffect(() => {
    processingRef.current = processing
  }, [processing])

  useEffect(() => {
    onCancelRef.current = onCancel
  }, [onCancel])

  useEffect(() => {
    const viewport = viewportRef.current
    if (!viewport) return

    const updateSize = () => setViewportSize(viewport.clientWidth || 256)
    updateSize()
    if (typeof ResizeObserver === 'undefined') {
      window.addEventListener('resize', updateSize)
      return () => window.removeEventListener('resize', updateSize)
    }
    const observer = new ResizeObserver(updateSize)
    observer.observe(viewport)
    return () => observer.disconnect()
  }, [])

  useEffect(() => {
    const previouslyFocusedElement =
      document.activeElement instanceof HTMLElement ? document.activeElement : null
    const previousOverflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    cancelButtonRef.current?.focus()

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        event.preventDefault()
        if (!processingRef.current) onCancelRef.current()
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

  const layout = dimensions
    ? avatarCropLayout(dimensions.width, dimensions.height, viewportSize, zoom)
    : null
  const displayOffset = layout ? clampAvatarOffset(offset, layout) : offset

  const updateOffset = useCallback(
    (nextOffset: AvatarOffset) => {
      if (!layout) return
      setOffset(clampAvatarOffset(nextOffset, layout))
    },
    [layout],
  )

  const handlePointerDown = (event: ReactPointerEvent<HTMLDivElement>) => {
    if (!layout || processing) return
    event.currentTarget.setPointerCapture(event.pointerId)
    dragRef.current = {
      pointerId: event.pointerId,
      startX: event.clientX,
      startY: event.clientY,
      offset: displayOffset,
    }
  }

  const handlePointerMove = (event: ReactPointerEvent<HTMLDivElement>) => {
    const drag = dragRef.current
    if (!drag || drag.pointerId !== event.pointerId) return
    updateOffset({
      x: drag.offset.x + event.clientX - drag.startX,
      y: drag.offset.y + event.clientY - drag.startY,
    })
  }

  const endPointerDrag = (event: ReactPointerEvent<HTMLDivElement>) => {
    if (dragRef.current?.pointerId !== event.pointerId) return
    dragRef.current = null
    if (event.currentTarget.hasPointerCapture(event.pointerId))
      event.currentTarget.releasePointerCapture(event.pointerId)
  }

  const handleCropKeyDown = (event: ReactKeyboardEvent<HTMLDivElement>) => {
    const movement: Record<string, AvatarOffset> = {
      ArrowLeft: { x: -8, y: 0 },
      ArrowRight: { x: 8, y: 0 },
      ArrowUp: { x: 0, y: -8 },
      ArrowDown: { x: 0, y: 8 },
    }
    const delta = movement[event.key]
    if (!delta) return
    event.preventDefault()
    updateOffset({ x: displayOffset.x + delta.x, y: displayOffset.y + delta.y })
  }

  const handleApply = async () => {
    if (!imageRef.current || !dimensions || processing) return
    setProcessing(true)
    setError(null)
    try {
      const file = await createCroppedAvatarFile(
        imageRef.current,
        viewportSize,
        zoom,
        displayOffset,
      )
      onApply(file)
    } catch {
      setError('processingError')
      setProcessing(false)
    }
  }

  const titleId = `${id}-title`
  const descriptionId = `${id}-description`
  const errorId = error ? `${id}-error` : undefined

  return (
    <div
      ref={backdropRef}
      className="fixed inset-0 z-[100] flex items-center justify-center overflow-y-auto bg-black/70 p-4 backdrop-blur-sm"
      onClick={(event) => {
        if (event.target === event.currentTarget && !processing) onCancel()
      }}
    >
      <div
        ref={dialogRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        aria-describedby={errorId ? `${descriptionId} ${errorId}` : descriptionId}
        aria-busy={processing}
        tabIndex={-1}
        className="my-auto w-full max-w-xl rounded-2xl border border-border bg-card p-5 text-card-foreground shadow-2xl outline-none sm:p-6"
      >
        <h2 id={titleId} className="text-xl font-semibold leading-tight">
          {t('profileAvatar.cropTitle')}
        </h2>
        <p id={descriptionId} className="mt-2 text-sm leading-6 text-muted-foreground">
          {t('profileAvatar.cropDescription')}
        </p>

        <div className="mt-5 flex justify-center">
          <div
            ref={viewportRef}
            role="img"
            aria-label={t('profileAvatar.cropArea')}
            tabIndex={dimensions && !processing ? 0 : -1}
            className="relative size-64 max-w-full touch-none overflow-hidden rounded-2xl bg-zinc-950 shadow-inner outline-none ring-1 ring-border focus-visible:ring-2 focus-visible:ring-vgu-orange sm:size-80"
            onPointerDown={handlePointerDown}
            onPointerMove={handlePointerMove}
            onPointerUp={endPointerDrag}
            onPointerCancel={endPointerDrag}
            onKeyDown={handleCropKeyDown}
          >
            {source ? (
              <img
                ref={imageRef}
                src={source.url}
                alt=""
                draggable={false}
                className="pointer-events-none absolute left-1/2 top-1/2 max-w-none select-none"
                style={
                  dimensions && layout
                    ? {
                        width: dimensions.width * layout.scale,
                        height: dimensions.height * layout.scale,
                        transform: `translate(-50%, -50%) translate(${displayOffset.x}px, ${displayOffset.y}px)`,
                      }
                    : { opacity: 0 }
                }
                onLoad={(event) => {
                  const image = event.currentTarget
                  const dimensionError = validateAvatarSourceDimensions(
                    image.naturalWidth,
                    image.naturalHeight,
                  )
                  if (dimensionError) {
                    setError(dimensionError)
                    setDimensions(null)
                    return
                  }
                  setError(null)
                  setDimensions({ width: image.naturalWidth, height: image.naturalHeight })
                }}
                onError={() => {
                  setDimensions(null)
                  setError('decodeError')
                }}
              />
            ) : null}
            {!dimensions && !error ? (
              <span
                className="absolute inset-0 flex items-center justify-center text-zinc-300"
                role="status"
              >
                <LoaderCircle
                  className="size-6 animate-spin motion-reduce:animate-none"
                  aria-hidden="true"
                />
                <span className="sr-only">{t('profileAvatar.loadingCrop')}</span>
              </span>
            ) : null}
            <span
              aria-hidden="true"
              className="pointer-events-none absolute inset-3 rounded-full border-2 border-white/90 shadow-[0_0_0_999px_rgba(0,0,0,0.35)]"
            />
            {dimensions ? (
              <span className="pointer-events-none absolute bottom-3 left-1/2 flex -translate-x-1/2 items-center gap-1 rounded-full bg-black/65 px-3 py-1 text-xs font-medium text-white">
                <Move className="size-3.5" aria-hidden="true" />
                {t('profileAvatar.dragHint')}
              </span>
            ) : null}
          </div>
        </div>

        <label className="mt-5 block text-sm font-semibold" htmlFor={`${id}-zoom`}>
          <span className="mb-2 flex items-center gap-2">
            <ZoomIn className="size-4" aria-hidden="true" />
            {t('profileAvatar.zoom')}
          </span>
          <input
            id={`${id}-zoom`}
            type="range"
            min="1"
            max="3"
            step="0.01"
            value={zoom}
            disabled={!dimensions || processing}
            className="w-full accent-vgu-orange"
            onChange={(event) => setZoom(Number(event.currentTarget.value))}
          />
        </label>

        {source ? (
          <p className="mt-3 truncate text-xs text-muted-foreground">{source.file.name}</p>
        ) : null}
        {error ? (
          <p
            id={errorId}
            role="alert"
            className="mt-4 rounded-xl border border-destructive/40 bg-destructive/10 px-3 py-2 text-sm text-destructive"
          >
            {t(`profileAvatar.errors.${error}`)}
          </p>
        ) : null}

        <div className="mt-6 flex flex-col-reverse gap-3 sm:flex-row sm:justify-end">
          <Button
            ref={cancelButtonRef}
            type="button"
            variant="secondary"
            disabled={processing}
            onClick={onCancel}
          >
            {t('profileAvatar.cancelCrop')}
          </Button>
          <Button
            type="button"
            disabled={!dimensions || Boolean(error) || processing}
            onClick={() => void handleApply()}
          >
            {processing ? (
              <LoaderCircle
                className="animate-spin motion-reduce:animate-none"
                aria-hidden="true"
              />
            ) : null}
            {processing ? t('profileAvatar.processingCrop') : t('profileAvatar.applyCrop')}
          </Button>
        </div>
      </div>
    </div>
  )
}

function AvatarCropDialog({ open, ...props }: AvatarCropDialogProps) {
  if (!open || typeof document === 'undefined') return null
  return createPortal(<AvatarCropDialogContent {...props} />, document.body)
}

export { AvatarCropDialog }
export type { AvatarCropDialogProps, AvatarCropSource }
