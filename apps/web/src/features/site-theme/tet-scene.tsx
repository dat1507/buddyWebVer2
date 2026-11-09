import type { CSSProperties } from 'react'

const apricot = [
  [485, 144, 1.1],
  [522, 124, 0.82],
  [552, 152, 1.2],
  [595, 103, 0.83],
  [609, 164, 0.92],
  [578, 193, 0.75],
] as const

const peach = [
  [47, 121, 0.84],
  [76, 150, 1.2],
  [111, 118, 0.78],
  [130, 161, 1],
  [165, 140, 0.75],
  [188, 172, 0.66],
] as const

function Blossoms({ pink }: { pink: boolean }) {
  return (pink ? peach : apricot).map(([x, y, size]) => (
    <g key={x} transform={`translate(${x} ${y}) scale(${size})`}>
      {[0, 72, 144, 216, 288].map((angle) => (
        <path
          key={angle}
          transform={`rotate(${angle})`}
          d={
            pink
              ? 'M0 2C-15-1-18-18-8-20q5-2 8 3 3-5 8-3C18-18 15-1 0 2Z'
              : 'M0 2C-10-2-16-13-9-20q9-8 18 0C16-13 10-2 0 2Z'
          }
          fill={pink ? '#f5a4b1' : '#ffd56a'}
          stroke={pink ? '#ba536d' : '#b87321'}
          strokeWidth=".8"
        />
      ))}
      <circle r="5" fill={pink ? '#a73f55' : '#a65b1d'} />
      <path d="M-7-2 7 2M0-7v14m-5-2 10-10" stroke="#fff2c7" strokeWidth="1.1" />
    </g>
  ))
}

export function TetScene() {
  return (
    <>
      <g fill="none" stroke="#6c4934" strokeWidth="4" strokeLinecap="round">
        <path d="M-8 77q61 77 135 79 36 4 75 18M42 124l6-19m31 44 31-31m23 38 32-16" />
        <path d="M652 54q-55 77-105 95-37 15-69-5m105-17 12-24m-49 45-24-24m43 16 13 53m13-65 18 36" />
      </g>
      <g fill="#688157">
        <path d="M142 160q20-19 30-12-6 13-30 12ZM520 153q-20 10-30 1 12-6 30-1ZM570 160q6-19 21-22-2 14-21 22Z" />
      </g>
      <Blossoms pink />
      <Blossoms pink={false} />
      <g transform="translate(561 222)">
        <path d="M0-43v43" stroke="#e8bc69" strokeWidth="2" />
        <g className="tet-envelope">
          <rect
            x="-23"
            width="46"
            height="74"
            rx="4"
            fill="#a82636"
            stroke="#f0c874"
            strokeWidth="2"
          />
          <path
            d="m-22 3 22 17L22 3m-39 63V9m34 57V9"
            fill="none"
            stroke="#f0c874"
            strokeWidth="1.1"
          />
          <path
            d="M0 29c-6-9-14-2-9 4-11-2-12 9-4 11-6 8 4 14 9 7 5 9 15 3 11-4 10-1 11-11 1-12 4-7-4-12-8-6Z"
            fill="#f0c874"
          />
          <circle cx="0" cy="41" r="3" fill="#a82636" />
        </g>
      </g>
      <g transform="translate(601 306) rotate(12)">
        <rect
          x="-16"
          width="32"
          height="50"
          rx="3"
          fill="#8e2632"
          stroke="#f0c874"
          strokeWidth="1.5"
        />
        <path
          d="m-15 3 15 12L15 3M-7 31l7-7 7 7-7 7Z"
          fill="none"
          stroke="#f0c874"
          strokeWidth="1.4"
        />
      </g>
      {Array.from({ length: 12 }, (_, i) => (
        <g key={i} transform={`translate(${45 + ((i * 127) % 543)} ${35 + ((i * 53) % 120)})`}>
          <path
            className="tet-petal"
            d={
              i % 3 === 0
                ? 'M0 0C-7-10 3-17 10-11 12-4 5 3 0 0Z'
                : 'M0 0C-5-8 2-13 7-9 8-3 4 2 0 0Z'
            }
            fill={i % 2 ? '#ffd56a' : '#f5a4b1'}
            style={
              {
                '--petal-duration': `${13 + (i % 5) * 2}s`,
                '--petal-delay': `${-i * 2.7}s`,
                '--petal-drift': `${i % 2 ? 38 : -32}px`,
              } as CSSProperties
            }
          />
        </g>
      ))}
    </>
  )
}
