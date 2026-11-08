import type { CSSProperties } from 'react'

// Deterministic scatter avoids hydration shifts and needs no animation timers.
export function ChristmasLandingEffects({ paused }: { paused: boolean }) {
  return (
    <div className="christmas-landing-effects" data-paused={paused || undefined} aria-hidden="true">
      <div className="christmas-snowfield">
        {Array.from({ length: 24 }, (_, i) => (
          <svg
            key={i}
            className="christmas-falling-flake"
            viewBox="0 0 24 24"
            style={
              {
                left: `${(i * 43.7 + 3) % 98}%`,
                width: `${10 + ((i * 7) % 14)}px`,
                '--fall-duration': `${15 + ((i * 3.1) % 14)}s`,
                '--fall-delay': `${-i * 3.7}s`,
                '--fall-drift': `${(i % 2 ? 1 : -1) * (12 + (i % 23))}px`,
              } as CSSProperties
            }
          >
            <path d="M12 2v20M3.34 7l17.32 10M3.34 17 20.66 7M9 4l3 3 3-3M9 20l3-3 3 3M4 10l4-1-1-4m10 14-1-4 4-1M4 14l4 1-1 4M17 5l-1 4 4 1" />
          </svg>
        ))}
      </div>
      <svg className="christmas-navbar-lights" viewBox="0 0 1200 42" preserveAspectRatio="none">
        <path
          d="M0 2Q100 42 200 2Q300 42 400 2Q500 42 600 2Q700 42 800 2Q900 42 1000 2Q1100 42 1200 2"
          fill="none"
          stroke="#75938a"
          strokeWidth="1.5"
        />
        {Array.from({ length: 30 }, (_, i) => {
          const x = 20 + i * 40
          const local = x % 200
          const y = 2 + 80 * (local / 200) * (1 - local / 200)
          return (
            <g key={i} transform={`translate(${x} ${y})`}>
              <path d="M0 0v7" stroke="#75938a" strokeWidth="1.5" />
              <g
                className="christmas-light"
                style={{ '--light-delay': `${-i * 0.7}s` } as CSSProperties}
              >
                <ellipse
                  cy="14"
                  rx="9"
                  ry="12"
                  fill={['#458e65', '#c45660', '#e7b64d'][i % 3]}
                  opacity=".16"
                />
                <ellipse cy="14" rx="3.5" ry="6" fill={['#458e65', '#c45660', '#e7b64d'][i % 3]} />
                <path d="M-1 11v3" stroke="#fff6d9" strokeWidth="1.2" strokeLinecap="round" />
              </g>
            </g>
          )
        })}
      </svg>
    </div>
  )
}
