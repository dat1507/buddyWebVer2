import { useContext, useEffect, useRef } from 'react'
import { LandingMotionContext } from '@/components/landing/landing-motion'
import { useSiteTheme } from './site-theme'
import { tetPetalColors, tetPetalPaths } from './tet-petals'
import './tet-section-effects.css'

const petals = [
  ['left', 'apricot', '15%', 12, -32],
  ['right', 'peach', '27%', 11, 28],
  ['left', 'peach', '46%', 8, 62],
  ['right', 'apricot', '57%', 13, -17],
  ['left', 'apricot', '72%', 10, 32],
  ['right', 'peach', '86%', 9, -51],
] as const

function TetSectionDecoration() {
  const { paused } = useContext(LandingMotionContext)
  const layerRef = useRef<HTMLDivElement>(null)
  const sparkleRef = useRef<SVGSVGElement>(null)

  useEffect(() => {
    const layer = layerRef.current
    const sparkle = sparkleRef.current
    if (paused || !layer || !sparkle || typeof window.matchMedia !== 'function') return

    const motion = window.matchMedia(
      '(min-width: 768px) and (prefers-reduced-motion: no-preference)',
    )
    const wide = window.matchMedia('(min-width: 1280px)')
    let frame = 0
    let observer: IntersectionObserver | undefined

    const scheduleDrift = () => {
      if (frame) return
      frame = requestAnimationFrame(() => {
        frame = 0
        const { top, bottom } = layer.getBoundingClientRect()
        const viewport = window.innerHeight
        if (bottom < 0 || top > viewport) return
        const progress = (viewport - top) / (viewport + bottom - top)
        layer.style.setProperty(
          '--tet-scroll-drift',
          `${(0.5 - progress) * (wide.matches ? 36 : 16)}px`,
        )
      })
    }

    const stop = () => {
      window.removeEventListener('scroll', scheduleDrift)
      window.removeEventListener('resize', scheduleDrift)
      cancelAnimationFrame(frame)
      frame = 0
      observer?.disconnect()
      observer = undefined
    }

    const syncMotion = () => {
      stop()
      if (!motion.matches) return
      window.addEventListener('scroll', scheduleDrift, { passive: true })
      window.addEventListener('resize', scheduleDrift)
      scheduleDrift()

      if (sparkle.hasAttribute('data-sparkled') || !('IntersectionObserver' in window)) return
      observer = new IntersectionObserver(
        (entries, activeObserver) => {
          if (activeObserver !== observer || !entries.some((entry) => entry.isIntersecting)) return
          sparkle.setAttribute('data-sparkled', '')
          activeObserver.disconnect()
        },
        { rootMargin: '-80px 0px -64px' },
      )
      observer.observe(sparkle)
    }

    motion.addEventListener('change', syncMotion)
    syncMotion()
    return () => {
      motion.removeEventListener('change', syncMotion)
      stop()
    }
  }, [paused])

  return (
    <div ref={layerRef} className="tet-scroll-effects" aria-hidden="true">
      {petals.map(([side, kind, top, size, angle]) => (
        <svg
          key={top}
          className={`tet-scroll-petal tet-scroll-petal-${side}`}
          style={{ top, rotate: `${angle}deg` }}
          width={size}
          height={size}
          viewBox="-8 -15 22 22"
          focusable="false"
        >
          <path
            d={tetPetalPaths[kind]}
            fill={tetPetalColors[kind]}
            stroke="#9e523c"
            strokeWidth="1"
          />
        </svg>
      ))}
      <svg ref={sparkleRef} className="tet-section-sparkles" viewBox="0 0 32 32" focusable="false">
        <g fill="#ffdc80" stroke="#b87924" strokeWidth=".75" strokeLinejoin="round">
          <path d="m16 6 2.3 7.7L26 16l-7.7 2.3L16 26l-2.3-7.7L6 16l7.7-2.3Z" />
          <path d="m6 3 1 3 3 1-3 1-1 3-1-3-3-1 3-1Zm21 19 1 3 3 1-3 1-1 3-1-3-3-1 3-1Z" />
        </g>
      </svg>
    </div>
  )
}

export function TetSectionEffects() {
  const theme = useSiteTheme()
  return theme === 'tet' ? <TetSectionDecoration /> : null
}
