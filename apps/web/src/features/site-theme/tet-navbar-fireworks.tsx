import './tet-navbar-fireworks.css'

export function TetNavbarFireworks() {
  return (
    <div className="tet-navbar-fireworks" aria-hidden="true">
      <svg className="tet-firework-trail" viewBox="0 0 1200 18" preserveAspectRatio="none">
        <path
          d="M0 13Q50 18 100 13T200 13 300 13 400 13 500 13 600 13 700 13 800 13 900 13 1000 13 1100 13 1200 13"
          fill="none"
          stroke="currentColor"
          strokeDasharray="1 5"
          strokeLinecap="round"
          vectorEffect="non-scaling-stroke"
        />
      </svg>
      <div className="tet-firework-row">
        {Array.from({ length: 11 }, (_, index) => (
          <svg
            key={index}
            className="tet-firework-cluster"
            viewBox="0 0 54 22"
            focusable="false"
            style={{ animationDelay: `${-index * 0.62}s` }}
          >
            <path
              className="tet-firework-rays"
              d="M27 7V2m0 13v4m-4-10-4-4m12 4 4-4m-12 7h-6m14 0h6m-14 3-3 3m11-3 3 3"
              fill="none"
              stroke="currentColor"
              strokeLinecap="round"
              strokeWidth="1.4"
            />
            <circle cx="27" cy="11.5" r="1.6" fill="#a82f3e" />
            <path
              d="M9 6l1 2 2 1-2 1-1 2-1-2-2-1 2-1ZM44 9l1 2 2 1-2 1-1 2-1-2-2-1 2-1Z"
              fill="currentColor"
            />
            <circle cx="4" cy="16" r="1" fill="#be6571" />
            <circle cx="50" cy="5" r="1" fill="#d3a050" />
          </svg>
        ))}
      </div>
    </div>
  )
}
