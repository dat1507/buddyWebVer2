import { useEffect, useRef, useState } from 'react'

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

type Layer = 0 | 1
type SlideshowPhase = 'display' | 'transition'

interface SlideshowState {
  activeLayer: Layer
  layerIndices: [number, number]
  phase: SlideshowPhase
}

function otherLayer(layer: Layer): Layer {
  return layer === 0 ? 1 : 0
}

function usePrefersReducedMotion(): boolean {
  const [reducedMotion, setReducedMotion] = useState(
    () =>
      typeof window.matchMedia === 'function' &&
      window.matchMedia('(prefers-reduced-motion: reduce)').matches,
  )

  useEffect(() => {
    if (typeof window.matchMedia !== 'function') return
    const mediaQuery = window.matchMedia('(prefers-reduced-motion: reduce)')
    const updatePreference = () => setReducedMotion(mediaQuery.matches)

    mediaQuery.addEventListener('change', updatePreference)
    return () => mediaQuery.removeEventListener('change', updatePreference)
  }, [])

  return reducedMotion
}

async function ensureImageDecoded(image: HTMLImageElement): Promise<void> {
  if (typeof image.decode === 'function') {
    try {
      await image.decode()
      return
    } catch (error) {
      if (image.complete && image.naturalWidth > 0) return
      throw error
    }
  }

  if (image.complete) {
    if (image.naturalWidth > 0) return
    throw new Error('Slideshow image failed to load.')
  }

  await new Promise<void>((resolve, reject) => {
    const onLoad = () => resolve()
    const onError = () => reject(new Error('Slideshow image failed to load.'))

    image.addEventListener('load', onLoad, { once: true })
    image.addEventListener('error', onError, { once: true })
  })
}

function startVisibleTimer(callback: () => void, durationMs: number): () => void {
  let remainingMs = durationMs
  let startedAt = 0
  let timer: number | undefined
  let finished = false

  const pause = () => {
    if (timer === undefined) return
    window.clearTimeout(timer)
    timer = undefined
    remainingMs = Math.max(0, remainingMs - (Date.now() - startedAt))
  }

  const start = () => {
    if (finished || document.hidden || timer !== undefined) return
    startedAt = Date.now()
    timer = window.setTimeout(() => {
      timer = undefined
      finished = true
      document.removeEventListener('visibilitychange', onVisibilityChange)
      callback()
    }, remainingMs)
  }

  const onVisibilityChange = () => {
    if (document.hidden) pause()
    else start()
  }

  document.addEventListener('visibilitychange', onVisibilityChange)
  start()

  return () => {
    finished = true
    if (timer !== undefined) window.clearTimeout(timer)
    document.removeEventListener('visibilitychange', onVisibilityChange)
  }
}

function HeroBackgroundSlideshow() {
  const reducedMotion = usePrefersReducedMotion()
  const imageRefs = useRef<[HTMLImageElement | null, HTMLImageElement | null]>([null, null])
  const [slideshow, setSlideshow] = useState<SlideshowState>({
    activeLayer: 0,
    layerIndices: [0, 1],
    phase: 'display',
  })

  useEffect(() => {
    if (reducedMotion || heroBackgrounds.length < 2) return

    if (slideshow.phase === 'transition') {
      const outgoingImage = imageRefs.current[slideshow.activeLayer]
      let completed = false

      const completeTransition = () => {
        if (completed) return
        completed = true
        setSlideshow((previous) => {
          if (previous.phase !== 'transition') return previous

          const nextActiveLayer = otherLayer(previous.activeLayer)
          const nextVisibleIndex = previous.layerIndices[nextActiveLayer]
          const nextLayerIndices: [number, number] = [...previous.layerIndices]

          // The outgoing layer is fully transparent here, so changing only its source cannot flash.
          nextLayerIndices[previous.activeLayer] = (nextVisibleIndex + 1) % heroBackgrounds.length

          return {
            activeLayer: nextActiveLayer,
            layerIndices: nextLayerIndices,
            phase: 'display',
          }
        })
      }

      const onTransitionEnd = (event: TransitionEvent) => {
        if (event.target === outgoingImage && event.propertyName === 'opacity') completeTransition()
      }

      outgoingImage?.addEventListener('transitionend', onTransitionEnd)

      return () => {
        outgoingImage?.removeEventListener('transitionend', onTransitionEnd)
      }
    }

    const incomingLayer = otherLayer(slideshow.activeLayer)
    const incomingImage = imageRefs.current[incomingLayer]
    if (!incomingImage) return

    let cancelled = false
    let displayElapsed = false
    let imageDecoded = false

    const startTransitionIfReady = () => {
      if (cancelled || !displayElapsed || !imageDecoded || document.hidden) return
      setSlideshow((previous) =>
        previous.phase === 'display' ? { ...previous, phase: 'transition' } : previous,
      )
    }

    const onVisibilityChange = () => startTransitionIfReady()
    document.addEventListener('visibilitychange', onVisibilityChange)

    const stopDisplayTimer = startVisibleTimer(() => {
      displayElapsed = true
      startTransitionIfReady()
    }, DISPLAY_DURATION_MS)

    void ensureImageDecoded(incomingImage)
      .then(() => {
        imageDecoded = true
        startTransitionIfReady()
      })
      .catch(() => {
        // Keep the decoded current image visible rather than crossfading to an unavailable source.
      })

    return () => {
      cancelled = true
      stopDisplayTimer()
      document.removeEventListener('visibilitychange', onVisibilityChange)
    }
  }, [reducedMotion, slideshow])

  if (reducedMotion) {
    return (
      <div
        className="pointer-events-none absolute inset-0 bg-black"
        aria-hidden="true"
        data-testid="hero-background-slideshow"
        data-phase="reduced-motion"
      >
        <img
          src={heroBackgrounds[0]}
          alt=""
          className="absolute inset-0 size-full object-cover"
          decoding="async"
          fetchPriority="high"
          loading="eager"
          data-testid="hero-background-static"
          data-slide-index="0"
        />
      </div>
    )
  }

  const incomingLayer = otherLayer(slideshow.activeLayer)

  return (
    <div
      className="pointer-events-none absolute inset-0 bg-black [contain:paint]"
      aria-hidden="true"
      data-testid="hero-background-slideshow"
      data-phase={slideshow.phase}
    >
      {slideshow.layerIndices.map((slideIndex, layerIndex) => {
        const layer = layerIndex as Layer
        const isVisible =
          slideshow.phase === 'display' ? layer === slideshow.activeLayer : layer === incomingLayer

        return (
          <img
            key={layer}
            ref={(image) => {
              imageRefs.current[layer] = image
            }}
            src={heroBackgrounds[slideIndex]}
            alt=""
            className={`absolute inset-0 size-full object-cover transition-opacity duration-1000 ease-in-out will-change-[opacity] ${
              isVisible ? 'opacity-100' : 'opacity-0'
            }`}
            decoding="async"
            fetchPriority={isVisible ? 'high' : 'low'}
            loading="eager"
            draggable={false}
            data-testid={`hero-background-layer-${layer}`}
            data-slide-index={slideIndex}
          />
        )
      })}
    </div>
  )
}

export { HeroBackgroundSlideshow }
export { DISPLAY_DURATION_MS, TRANSITION_DURATION_MS }
