import { useEffect, useState } from 'react'

import campusExterior from '@/assets/landing-backgrounds/01-campus-exterior.webp'
import campusAerial from '@/assets/landing-backgrounds/02-campus-aerial.webp'
import campusGarden from '@/assets/landing-backgrounds/03-campus-garden.webp'
import campusArchitecture from '@/assets/landing-backgrounds/04-campus-architecture.webp'
import campusLibrary from '@/assets/landing-backgrounds/05-campus-library.webp'

const DISPLAY_DURATION_MS = 7_000
const TRANSITION_DURATION_MS = 1_000

// Stable owner-supplied order: exterior, aerial, garden, architecture, library.
const heroBackgrounds = [
  campusExterior,
  campusAerial,
  campusGarden,
  campusArchitecture,
  campusLibrary,
] as const

function usePrefersReducedMotion(): boolean {
  const [reducedMotion, setReducedMotion] = useState(false)

  useEffect(() => {
    if (typeof window.matchMedia !== 'function') return
    const mediaQuery = window.matchMedia('(prefers-reduced-motion: reduce)')
    const updatePreference = () => setReducedMotion(mediaQuery.matches)

    updatePreference()
    mediaQuery.addEventListener('change', updatePreference)
    return () => mediaQuery.removeEventListener('change', updatePreference)
  }, [])

  return reducedMotion
}

function HeroBackgroundSlideshow() {
  const reducedMotion = usePrefersReducedMotion()
  const [currentIndex, setCurrentIndex] = useState(0)
  const [nextIndex, setNextIndex] = useState(1)
  const [transitioning, setTransitioning] = useState(false)
  const isTransitioning = transitioning && !reducedMotion

  useEffect(() => {
    if (reducedMotion || heroBackgrounds.length < 2) return

    const transitionTimer = window.setTimeout(() => {
      setTransitioning(true)
    }, DISPLAY_DURATION_MS)
    const completionTimer = window.setTimeout(() => {
      setCurrentIndex(nextIndex)
      setNextIndex((nextIndex + 1) % heroBackgrounds.length)
      setTransitioning(false)
    }, DISPLAY_DURATION_MS + TRANSITION_DURATION_MS)

    return () => {
      window.clearTimeout(transitionTimer)
      window.clearTimeout(completionTimer)
    }
  }, [currentIndex, nextIndex, reducedMotion])

  return (
    <div
      className="pointer-events-none absolute inset-0 bg-black"
      aria-hidden="true"
      data-testid="hero-background-slideshow"
    >
      <img
        src={heroBackgrounds[currentIndex]}
        alt=""
        className={`absolute inset-0 size-full object-cover transition-opacity duration-1000 ease-in-out motion-reduce:transition-none ${
          isTransitioning ? 'opacity-0' : 'opacity-100'
        }`}
        decoding="async"
        fetchPriority="high"
        data-testid="hero-background-current"
        data-slide-index={currentIndex}
      />
      {!reducedMotion ? (
        <img
          src={heroBackgrounds[nextIndex]}
          alt=""
          className={`absolute inset-0 size-full object-cover transition-opacity duration-1000 ease-in-out ${
            isTransitioning ? 'opacity-100' : 'opacity-0'
          }`}
          decoding="async"
          fetchPriority="low"
          data-testid="hero-background-next"
          data-slide-index={nextIndex}
        />
      ) : null}
    </div>
  )
}

export { HeroBackgroundSlideshow }
export { DISPLAY_DURATION_MS, TRANSITION_DURATION_MS }
