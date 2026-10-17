import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  type TouchEvent,
  type TransitionEvent,
} from 'react'
import { ChevronLeft, ChevronRight, ImageOff } from 'lucide-react'
import { useTranslation } from 'react-i18next'

import { Button } from '@/components/ui/button'
import { Typography } from '@/components/ui/typography'
import type { EventSlider } from '@/features/events/event-slider'
import { cn } from '@/lib/utils'

const autoplayDelay = 3_000
const swipeThreshold = 48

interface EventsSliderProps {
  events: readonly EventSlider[]
}

interface CarouselSlide {
  event: EventSlider
  clone: boolean
  key: string
}

function usePrefersReducedMotion() {
  const [prefersReducedMotion, setPrefersReducedMotion] = useState(() =>
    typeof window === 'undefined'
      ? false
      : window.matchMedia('(prefers-reduced-motion: reduce)').matches,
  )

  useEffect(() => {
    const mediaQuery = window.matchMedia('(prefers-reduced-motion: reduce)')
    const handleChange = () => setPrefersReducedMotion(mediaQuery.matches)

    mediaQuery.addEventListener('change', handleChange)
    return () => mediaQuery.removeEventListener('change', handleChange)
  }, [])

  return prefersReducedMotion
}

function EventSlide({
  slide,
  active,
  clone,
}: {
  slide: EventSlider
  active: boolean
  clone: boolean
}) {
  const { t } = useTranslation()
  const [failedImageUrl, setFailedImageUrl] = useState<string | null>(null)
  const imageFailed = failedImageUrl === slide.imageUrl
  const card = (
    <div className="overflow-hidden rounded-2xl border border-white/10 bg-black shadow-2xl transition-colors group-hover:border-orange-500/50">
      <div className="flex aspect-[5/4] items-center justify-center bg-black">
        {imageFailed ? (
          <div
            role={clone ? undefined : 'img'}
            aria-label={clone ? undefined : t('eventDetail.noCover')}
            className="flex size-full items-center justify-center bg-zinc-950 text-zinc-600"
          >
            <ImageOff aria-hidden="true" className="size-12" />
          </div>
        ) : (
          <img
            src={slide.imageUrl}
            alt={clone ? '' : slide.imageAlt}
            className="h-full w-full select-none object-contain"
            loading="eager"
            decoding="async"
            draggable={false}
            onError={() => setFailedImageUrl(slide.imageUrl)}
          />
        )}
      </div>

      <div className="flex min-h-24 items-center justify-center border-t border-white/10 bg-zinc-950 px-5 py-4 sm:px-6">
        <Typography variant="h3" className="text-center text-xl sm:text-2xl">
          {slide.title}
        </Typography>
      </div>
    </div>
  )

  return (
    <article
      className="w-full shrink-0"
      aria-hidden={!active || clone}
      aria-roledescription="slide"
    >
      {slide.cta ? (
        <a
          href={slide.cta.href}
          tabIndex={active && !clone ? 0 : -1}
          aria-label={`${slide.cta.label}: ${slide.title}`}
          className="group block rounded-2xl outline-none focus-visible:ring-2 focus-visible:ring-orange-500 focus-visible:ring-offset-4 focus-visible:ring-offset-black"
        >
          {card}
        </a>
      ) : (
        card
      )}
    </article>
  )
}

function EventCarousel({ events }: { events: readonly EventSlider[] }) {
  const { t } = useTranslation()
  const prefersReducedMotion = usePrefersReducedMotion()
  const [slideIndex, setSlideIndex] = useState(events.length > 1 ? 1 : 0)
  const [isTransitionEnabled, setIsTransitionEnabled] = useState(true)
  const [isTransitioning, setIsTransitioning] = useState(false)
  const [isPointerPaused, setIsPointerPaused] = useState(false)
  const [isFocusPaused, setIsFocusPaused] = useState(false)
  const isTransitioningRef = useRef(false)
  const pendingDirectionsRef = useRef<Array<-1 | 1>>([])
  const resumeFrameRef = useRef<number | null>(null)
  const touchStartRef = useRef<{ x: number; y: number } | null>(null)
  const isPaused = prefersReducedMotion || isPointerPaused || isFocusPaused

  const slides = useMemo<CarouselSlide[]>(() => {
    if (events.length <= 1) {
      return events.map((event) => ({ event, clone: false, key: event.id }))
    }

    const firstEvent = events[0]
    const lastEvent = events[events.length - 1]

    return [
      { event: lastEvent, clone: true, key: `${lastEvent.id}-leading-clone` },
      ...events.map((event) => ({ event, clone: false, key: event.id })),
      { event: firstEvent, clone: true, key: `${firstEvent.id}-trailing-clone` },
    ]
  }, [events])

  useEffect(() => {
    if (isTransitionEnabled) return

    const animationFrame = window.requestAnimationFrame(() => setIsTransitionEnabled(true))
    return () => window.cancelAnimationFrame(animationFrame)
  }, [isTransitionEnabled])

  useEffect(
    () => () => {
      if (resumeFrameRef.current !== null) window.cancelAnimationFrame(resumeFrameRef.current)
    },
    [],
  )

  const moveSlide = useCallback(
    (direction: -1 | 1) => {
      if (events.length <= 1) return

      if (prefersReducedMotion) {
        pendingDirectionsRef.current = []
        setSlideIndex(
          (currentIndex) => ((currentIndex - 1 + direction + events.length) % events.length) + 1,
        )
        return
      }

      if (isTransitioningRef.current) {
        pendingDirectionsRef.current.push(direction)
        return
      }

      isTransitioningRef.current = true
      setIsTransitioning(true)
      setSlideIndex((currentIndex) => currentIndex + direction)
    },
    [events.length, prefersReducedMotion],
  )

  useEffect(() => {
    if (events.length <= 1 || isPaused || isTransitioning) return

    const autoplayTimer = window.setTimeout(() => moveSlide(1), autoplayDelay)
    return () => window.clearTimeout(autoplayTimer)
  }, [events.length, isPaused, isTransitioning, moveSlide, slideIndex])

  const handleTransitionEnd = (event: TransitionEvent<HTMLDivElement>) => {
    if (event.currentTarget !== event.target || event.propertyName !== 'transform') return
    if (events.length <= 1) return

    const crossedLoopBoundary = slideIndex === 0 || slideIndex === events.length + 1
    if (slideIndex === 0) {
      setIsTransitionEnabled(false)
      setSlideIndex(events.length)
    } else if (slideIndex === events.length + 1) {
      setIsTransitionEnabled(false)
      setSlideIndex(1)
    }

    const needsResumeFrame = crossedLoopBoundary || pendingDirectionsRef.current.length > 0
    isTransitioningRef.current = needsResumeFrame
    setIsTransitioning(needsResumeFrame)

    if (!needsResumeFrame) return

    const continueQueuedNavigation = () => {
      if (crossedLoopBoundary) setIsTransitionEnabled(true)
      const direction = pendingDirectionsRef.current.shift()
      resumeFrameRef.current = null
      if (direction === undefined) {
        isTransitioningRef.current = false
        setIsTransitioning(false)
        return
      }
      isTransitioningRef.current = true
      setIsTransitioning(true)
      setSlideIndex((currentIndex) => currentIndex + direction)
    }

    if (crossedLoopBoundary) {
      resumeFrameRef.current = window.requestAnimationFrame(() => {
        resumeFrameRef.current = window.requestAnimationFrame(continueQueuedNavigation)
      })
    } else {
      resumeFrameRef.current = window.requestAnimationFrame(continueQueuedNavigation)
    }
  }

  const handleTouchStart = (event: TouchEvent<HTMLDivElement>) => {
    const touch = event.touches[0]
    touchStartRef.current = touch ? { x: touch.clientX, y: touch.clientY } : null
  }

  const handleTouchEnd = (event: TouchEvent<HTMLDivElement>) => {
    const start = touchStartRef.current
    const touch = event.changedTouches[0]
    touchStartRef.current = null
    if (!start || !touch) return
    const horizontal = touch.clientX - start.x
    const vertical = touch.clientY - start.y
    if (Math.abs(horizontal) < swipeThreshold || Math.abs(horizontal) <= Math.abs(vertical)) return
    moveSlide(horizontal < 0 ? 1 : -1)
  }

  const logicalIndex = events.length <= 1 ? 0 : (slideIndex - 1 + events.length) % events.length

  return (
    <div
      className="relative mx-auto w-full max-w-4xl touch-pan-y"
      role="region"
      aria-roledescription="carousel"
      aria-label={t('stats.carouselLabel')}
      onMouseEnter={() => setIsPointerPaused(true)}
      onMouseLeave={() => setIsPointerPaused(false)}
      onTouchStart={handleTouchStart}
      onTouchEnd={handleTouchEnd}
      onTouchCancel={() => {
        touchStartRef.current = null
      }}
      onFocusCapture={() => setIsFocusPaused(true)}
      onBlurCapture={(event) => {
        const nextTarget = event.relatedTarget
        if (!(nextTarget instanceof Node) || !event.currentTarget.contains(nextTarget)) {
          setIsFocusPaused(false)
        }
      }}
    >
      <div className="overflow-hidden rounded-2xl">
        <div
          data-testid="event-slider-track"
          data-slide-index={logicalIndex}
          data-transitioning={isTransitioning ? 'true' : 'false'}
          className={cn(
            'flex motion-reduce:transition-none',
            isTransitionEnabled && 'transition-transform duration-500',
          )}
          style={{
            backfaceVisibility: 'hidden',
            transform: `translate3d(-${slideIndex * 100}%, 0, 0)`,
            transitionTimingFunction: 'cubic-bezier(0.22, 1, 0.36, 1)',
            willChange: isTransitioning ? 'transform' : 'auto',
          }}
          onTransitionEnd={handleTransitionEnd}
        >
          {slides.map(({ event, clone, key }, index) => (
            <EventSlide key={key} slide={event} active={index === slideIndex} clone={clone} />
          ))}
        </div>
      </div>

      {events.length > 1 ? (
        <>
          <Button
            type="button"
            size="icon"
            variant="secondary"
            className="absolute left-3 top-[42%] rounded-full border-white/20 bg-black/75 text-white backdrop-blur-sm hover:bg-orange-500 hover:text-black sm:left-4"
            aria-label={t('stats.previousEvent')}
            onClick={() => moveSlide(-1)}
          >
            <ChevronLeft aria-hidden="true" />
          </Button>
          <Button
            type="button"
            size="icon"
            variant="secondary"
            className="absolute right-3 top-[42%] rounded-full border-white/20 bg-black/75 text-white backdrop-blur-sm hover:bg-orange-500 hover:text-black sm:right-4"
            aria-label={t('stats.nextEvent')}
            onClick={() => moveSlide(1)}
          >
            <ChevronRight aria-hidden="true" />
          </Button>
        </>
      ) : null}

      <p className="mt-4 text-center text-sm text-zinc-500" aria-live={isPaused ? 'polite' : 'off'}>
        {t('stats.slideStatus', { current: logicalIndex + 1, total: events.length })}
      </p>
    </div>
  )
}

function EventsSlider({ events }: EventsSliderProps) {
  const { t } = useTranslation()

  if (events.length === 0) return null

  return (
    <section
      id="events"
      className="scroll-mt-20 bg-vgu-surface px-4 py-16 sm:px-6 sm:py-20 lg:px-8"
      aria-labelledby="events-title"
    >
      <div className="mx-auto max-w-7xl">
        <div className="mx-auto mb-10 max-w-3xl text-center sm:mb-14">
          <Typography id="events-title" variant="h2">
            {t('stats.title')}
          </Typography>
          <Typography variant="lead" className="mt-5 text-zinc-400">
            {t('stats.subtitle')}
          </Typography>
        </div>

        <EventCarousel key={events.map((event) => event.id).join(':')} events={events} />
      </div>
    </section>
  )
}

export { EventsSlider }
