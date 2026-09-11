import { useEffect, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'

import { Card, CardContent } from '@/components/ui/card'
import { Typography } from '@/components/ui/typography'

const TESTIMONIAL_COUNT = 12
const SCROLL_SPEED_PX_PER_SECOND = 30
const REDUCED_MOTION_QUERY = '(prefers-reduced-motion: reduce)'

const testimonialKeys = Array.from({ length: TESTIMONIAL_COUNT }, (_, i) => `testimonial${i + 1}`)

/** Split testimonials into two rows for the two-row marquee layout. */
const topRowKeys = testimonialKeys.filter((_, i) => i % 2 === 0)
const bottomRowKeys = testimonialKeys.filter((_, i) => i % 2 !== 0)

function usePrefersReducedMotion() {
  const [prefersReducedMotion, setPrefersReducedMotion] = useState(() =>
    typeof window === 'undefined' ? false : window.matchMedia(REDUCED_MOTION_QUERY).matches,
  )

  useEffect(() => {
    const mediaQuery = window.matchMedia(REDUCED_MOTION_QUERY)
    const handleChange = () => setPrefersReducedMotion(mediaQuery.matches)

    handleChange()
    mediaQuery.addEventListener('change', handleChange)
    return () => mediaQuery.removeEventListener('change', handleChange)
  }, [])

  return prefersReducedMotion
}

/**
 * A single marquee row.
 *
 * The row duplicates its children so the seam is invisible.
 * Animation uses `requestAnimationFrame` and CSS `translateX` for
 * jank-free scrolling. Scrolling pauses when the pointer hovers
 * over the row or when `prefers-reduced-motion: reduce` is active.
 */
function MarqueeRow({ keys, direction }: { keys: readonly string[]; direction: 'left' | 'right' }) {
  const { t } = useTranslation()

  const trackRef = useRef<HTMLDivElement>(null)
  const offsetRef = useRef(0)
  const rafRef = useRef(0)
  const previousTimestampRef = useRef<number | null>(null)
  const pausedRef = useRef(false)
  const prefersReducedMotion = usePrefersReducedMotion()

  useEffect(() => {
    const track = trackRef.current
    if (!track || prefersReducedMotion) return

    // Initialise offset for right-scrolling rows so they start from the
    // "far" end and scroll toward 0.
    if (direction === 'right') {
      offsetRef.current = -(track.scrollWidth / 2)
      track.style.transform = `translateX(${offsetRef.current}px)`
    }

    previousTimestampRef.current = null

    function step(timestamp: number) {
      const currentTrack = trackRef.current
      if (!currentTrack) return

      const previousTimestamp = previousTimestampRef.current
      previousTimestampRef.current = timestamp

      if (!pausedRef.current && previousTimestamp !== null) {
        const halfWidth = currentTrack.scrollWidth / 2
        if (halfWidth > 0) {
          const sign = direction === 'left' ? -1 : 1
          const elapsedSeconds = Math.max(0, timestamp - previousTimestamp) / 1_000
          offsetRef.current += SCROLL_SPEED_PX_PER_SECOND * elapsedSeconds * sign

          // Reset when one full copy has scrolled past
          if (direction === 'left' && offsetRef.current <= -halfWidth) {
            offsetRef.current %= halfWidth
          } else if (direction === 'right' && offsetRef.current >= 0) {
            offsetRef.current = (offsetRef.current % halfWidth) - halfWidth
          }

          currentTrack.style.transform = `translateX(${offsetRef.current}px)`
        }
      }

      rafRef.current = window.requestAnimationFrame(step)
    }

    rafRef.current = window.requestAnimationFrame(step)
    return () => {
      window.cancelAnimationFrame(rafRef.current)
      previousTimestampRef.current = null
    }
  }, [prefersReducedMotion, direction])

  return (
    <div
      className="overflow-hidden"
      data-marquee-row={direction}
      onPointerEnter={() => {
        pausedRef.current = true
      }}
      onPointerLeave={() => {
        pausedRef.current = false
      }}
    >
      <div ref={trackRef} className="flex w-max gap-5" data-marquee-track={direction}>
        {/* Original + clone for seamless loop */}
        {[...keys, ...keys].map((key, i) => {
          const isVisualClone = i >= keys.length

          return (
            <Card
              key={`${key}-${i}`}
              className="w-[340px] shrink-0 border-white/10 bg-zinc-900/70 shadow-lg sm:w-[380px]"
              aria-hidden={isVisualClone || undefined}
              data-marquee-clone={isVisualClone || undefined}
            >
              <CardContent className="p-5 sm:p-6">
                <blockquote className="text-sm leading-relaxed text-zinc-300 sm:text-base">
                  &ldquo;{t(`community.${key}`)}&rdquo;
                </blockquote>
              </CardContent>
            </Card>
          )
        })}
      </div>
    </div>
  )
}

function TestimonialsMarquee() {
  const { t } = useTranslation()

  return (
    <section
      id="community"
      className="overflow-hidden bg-black px-4 py-16 sm:px-6 sm:py-20 lg:px-8"
      aria-labelledby="community-title"
    >
      <div className="mx-auto mb-12 max-w-7xl text-center sm:mb-16">
        <Typography id="community-title" variant="h2">
          {t('community.title')}
        </Typography>
        <Typography variant="lead" className="mx-auto mt-5 max-w-3xl text-zinc-400">
          {t('community.subtitle')}
        </Typography>
      </div>

      <div className="flex flex-col gap-5">
        <MarqueeRow keys={topRowKeys} direction="left" />
        <MarqueeRow keys={bottomRowKeys} direction="right" />
      </div>
    </section>
  )
}

export { TestimonialsMarquee }
