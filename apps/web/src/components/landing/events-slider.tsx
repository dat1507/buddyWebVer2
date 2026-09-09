import { useCallback, useEffect, useMemo, useState } from 'react'
import { CalendarDays, ChevronLeft, ChevronRight, ExternalLink, MapPin } from 'lucide-react'
import { useTranslation } from 'react-i18next'

import { Button } from '@/components/ui/button'
import { Typography } from '@/components/ui/typography'
import type { EventSlider, EventSliderLocale } from '@/features/events/event-slider'
import { useEventSliders } from '@/features/events/queries/use-event-sliders'
import type { EventSliderRepository } from '@/features/events/repositories/event-slider-repository'
import { cn } from '@/lib/utils'

const autoplayDelay = 3_000

interface EventsSliderProps {
  repository?: EventSliderRepository
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

function formatEventDate(slide: EventSlider, locale: EventSliderLocale) {
  if (!slide.eventStartAt) return null

  const formatter = new Intl.DateTimeFormat(locale === 'de' ? 'de-DE' : 'en-US', {
    dateStyle: 'medium',
    timeStyle: 'short',
  })
  const start = formatter.format(new Date(slide.eventStartAt))

  if (!slide.eventEndAt) return start
  return `${start} – ${formatter.format(new Date(slide.eventEndAt))}`
}

function EventSlide({
  slide,
  active,
  clone,
  locale,
}: {
  slide: EventSlider
  active: boolean
  clone: boolean
  locale: EventSliderLocale
}) {
  const date = formatEventDate(slide, locale)
  const isExternalCta = slide.cta?.href.startsWith('https://') ?? false

  return (
    <article
      className="w-full shrink-0"
      aria-hidden={!active || clone}
      aria-roledescription="slide"
    >
      <div className="overflow-hidden rounded-2xl border border-white/10 bg-black shadow-2xl">
        <div className="aspect-[5/4] bg-black">
          <img
            src={slide.imageUrl}
            alt={clone ? '' : slide.imageAlt}
            className="h-full w-full object-contain"
            loading={active ? 'eager' : 'lazy'}
          />
        </div>

        <div className="min-h-32 border-t border-white/10 bg-zinc-950 px-5 py-4 sm:px-6">
          <Typography variant="h3" className="text-xl sm:text-2xl">
            {slide.title}
          </Typography>

          {slide.description ? (
            <p className="mt-2 text-base leading-7 text-zinc-400">{slide.description}</p>
          ) : null}

          {date || slide.location || slide.cta ? (
            <div className="mt-4 flex flex-wrap items-center gap-x-5 gap-y-3 text-sm text-zinc-400">
              {date ? (
                <span className="inline-flex items-center gap-2">
                  <CalendarDays aria-hidden="true" className="size-4 text-orange-500" />
                  {date}
                </span>
              ) : null}
              {slide.location ? (
                <span className="inline-flex items-center gap-2">
                  <MapPin aria-hidden="true" className="size-4 text-orange-500" />
                  {slide.location}
                </span>
              ) : null}
              {slide.cta ? (
                <Button
                  asChild
                  variant="link"
                  className="ml-auto"
                  tabIndex={active && !clone ? 0 : -1}
                >
                  <a
                    href={slide.cta.href}
                    target={isExternalCta ? '_blank' : undefined}
                    rel={isExternalCta ? 'noreferrer' : undefined}
                  >
                    {slide.cta.label}
                    {isExternalCta ? <ExternalLink aria-hidden="true" /> : null}
                  </a>
                </Button>
              ) : null}
            </div>
          ) : null}
        </div>
      </div>
    </article>
  )
}

function EventCarousel({ events, locale }: { events: EventSlider[]; locale: EventSliderLocale }) {
  const { t } = useTranslation()
  const prefersReducedMotion = usePrefersReducedMotion()
  const [slideIndex, setSlideIndex] = useState(events.length > 1 ? 1 : 0)
  const [isTransitionEnabled, setIsTransitionEnabled] = useState(true)
  const [isTransitioning, setIsTransitioning] = useState(false)
  const [isPointerPaused, setIsPointerPaused] = useState(false)
  const [isFocusPaused, setIsFocusPaused] = useState(false)
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

  const moveSlide = useCallback(
    (direction: -1 | 1) => {
      if (events.length <= 1 || isTransitioning) return

      if (prefersReducedMotion) {
        setSlideIndex(
          (currentIndex) => ((currentIndex - 1 + direction + events.length) % events.length) + 1,
        )
        return
      }

      setIsTransitioning(true)
      setSlideIndex((currentIndex) => currentIndex + direction)
    },
    [events.length, isTransitioning, prefersReducedMotion],
  )

  useEffect(() => {
    if (events.length <= 1 || isPaused || isTransitioning) return

    const autoplayTimer = window.setTimeout(() => moveSlide(1), autoplayDelay)
    return () => window.clearTimeout(autoplayTimer)
  }, [events.length, isPaused, isTransitioning, moveSlide, slideIndex])

  const handleTransitionEnd = () => {
    if (events.length <= 1) return

    if (slideIndex === 0) {
      setIsTransitionEnabled(false)
      setSlideIndex(events.length)
    } else if (slideIndex === events.length + 1) {
      setIsTransitionEnabled(false)
      setSlideIndex(1)
    }

    setIsTransitioning(false)
  }

  const logicalIndex = events.length <= 1 ? 0 : (slideIndex - 1 + events.length) % events.length

  return (
    <div
      className="relative mx-auto w-full max-w-4xl"
      role="region"
      aria-roledescription="carousel"
      aria-label={t('stats.carouselLabel')}
      onMouseEnter={() => setIsPointerPaused(true)}
      onMouseLeave={() => setIsPointerPaused(false)}
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
          className={cn(
            'flex motion-reduce:transition-none',
            isTransitionEnabled && 'transition-transform duration-700 ease-out',
          )}
          style={{ transform: `translateX(-${slideIndex * 100}%)` }}
          onTransitionEnd={handleTransitionEnd}
        >
          {slides.map(({ event, clone, key }, index) => (
            <EventSlide
              key={key}
              slide={event}
              active={index === slideIndex}
              clone={clone}
              locale={locale}
            />
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
            disabled={isTransitioning}
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
            disabled={isTransitioning}
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

function EventsSlider({ repository }: EventsSliderProps) {
  const { t, i18n } = useTranslation()
  const locale: EventSliderLocale = i18n.resolvedLanguage?.startsWith('de') ? 'de' : 'en'
  const { data: events, error, isPending, refetch } = useEventSliders(locale, repository)

  return (
    <section
      className="bg-vgu-surface px-4 py-16 sm:px-6 sm:py-20 lg:px-8"
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

        {isPending ? (
          <div
            className="mx-auto aspect-[5/4] w-full max-w-4xl animate-pulse rounded-2xl border border-white/10 bg-zinc-900 motion-reduce:animate-none"
            role="status"
          >
            <span className="sr-only">{t('stats.loading')}</span>
          </div>
        ) : error ? (
          <div
            className="mx-auto max-w-xl rounded-2xl border border-red-500/30 bg-red-950/20 p-8 text-center"
            role="alert"
          >
            <p className="text-base text-zinc-200">{t('stats.error')}</p>
            <Button className="mt-5" type="button" variant="outline" onClick={() => void refetch()}>
              {t('stats.retry')}
            </Button>
          </div>
        ) : events.length === 0 ? (
          <div
            className="mx-auto max-w-xl rounded-2xl border border-white/10 bg-black/30 p-8 text-center"
            role="status"
          >
            <CalendarDays aria-hidden="true" className="mx-auto size-10 text-orange-500" />
            <p className="mt-4 text-base text-zinc-300">{t('stats.empty')}</p>
          </div>
        ) : (
          <EventCarousel
            key={events.map((event) => event.id).join(':')}
            events={events}
            locale={locale}
          />
        )}
      </div>
    </section>
  )
}

export { EventsSlider }
