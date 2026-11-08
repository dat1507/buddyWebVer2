import type { ThemeId } from './site-theme'
import { ChristmasScene } from './christmas-scene'

type SeasonalTheme = Exclude<ThemeId, 'default'>

function Halloween() {
  return (
    <>
      <g
        className="season-scene-detail"
        fill="none"
        stroke="#e4cef9"
        strokeWidth="1.5"
        opacity=".65"
      >
        <path d="M18 2v178M18 2l98 154M18 2l160 89M18 2h190M18 46q18-2 25-4 8-3 10-19 3-5 4-21M18 82q32-2 43-14 8-14 27-27 7-10 9-39M18 119q46-4 62-23 13-22 42-38 12-13 15-56M18 158q59-6 82-34 17-28 58-46 15-15 20-76" />
      </g>
      <g className="season-scene-twinkle">
        <circle cx="483" cy="134" r="70" fill="#e7b4ff" opacity=".1" />
        <circle cx="483" cy="134" r="57" fill="#e7b4ff" opacity=".16" />
        <path d="M513 86a48 48 0 1 0 15 71 44 44 0 0 1-15-71Z" fill="#ffe4b1" />
        <path
          d="M403 100v16m-8-8h16m151 53v18m-9-9h18m-142 8v10m-5-5h10m-53-97v10m-5-5h10"
          stroke="#f5d4ff"
          strokeWidth="2"
          strokeLinecap="round"
        />
      </g>
      <g
        className="season-scene-flight"
        fill="#20162e"
        stroke="#ba8ddd"
        strokeWidth="1.4"
        strokeLinejoin="round"
      >
        <path d="M280 142q-16-18-40-15 13 7 11 18 17-3 27 14 12-11 27-3 2-11 16-14-23-10-36 1l-2-9Z" />
        <path d="M350 178q-10-11-24-10 8 5 7 11 10-2 16 9 8-7 17-2 2-7 11-9-15-6-23 1l-2-6Z" />
      </g>
      <g transform="translate(545 442)">
        <path d="M-6-34q-7-14 4-24 4 14 1 23" fill="#8da86e" />
        <ellipse cx="0" cy="-12" rx="42" ry="31" fill="#ad4f23" />
        <ellipse cx="0" cy="-12" rx="30" ry="31" fill="#e77e3c" />
        <ellipse cx="0" cy="-12" rx="17" ry="31" fill="#f99c55" />
        <path
          d="m-17-14 8-12 7 12Zm21 0 8-12 7 12ZM-14-3q13 10 29 0-5 14-15 14T-14-3"
          fill="#492032"
        />
      </g>
      <g className="season-scene-detail" transform="translate(598 462) scale(.62)">
        <path d="M0-37q-5-13 5-21l3 17" fill="#8da86e" />
        <ellipse cy="-13" rx="36" ry="28" fill="#aa5229" />
        <ellipse cy="-13" rx="23" ry="28" fill="#ee8d47" />
        <ellipse cy="-13" rx="12" ry="28" fill="#f7ab60" />
      </g>
    </>
  )
}

function Summer() {
  return (
    <>
      <g transform="translate(504 130)">
        <circle r="66" fill="#ffe28a" opacity=".13" />
        <circle r="45" fill="#ffdc75" stroke="#fff1bc" strokeWidth="2" />
        <path
          d="M0-58v-12m0 128v12m58-70h12m-128 0h-12m111-41 9-9m-91 91-9 9m91-9 9 9m-91-91-9-9"
          fill="none"
          stroke="#ffe68e"
          strokeWidth="4"
          strokeLinecap="round"
        />
      </g>
      <g className="season-scene-clouds" fill="#fff9ea">
        <path
          d="M187 129a18 18 0 0 1 19-18 26 26 0 0 1 48 4 17 17 0 0 1 19 18H186Z"
          opacity=".85"
        />
        <path
          className="season-scene-detail"
          d="M304 88a12 12 0 0 1 13-11 18 18 0 0 1 34 2 12 12 0 0 1 13 12h-60Z"
          opacity=".74"
        />
      </g>
      <g className="season-scene-surf">
        <path d="M-32 494q112-63 234-10t236-6 238-18v118H-32Z" fill="#2cb4bc" opacity=".62" />
        <path
          d="M-32 510q110-51 238-5t228-9 242-20"
          fill="none"
          stroke="#b7f1e8"
          strokeWidth="3"
          opacity=".84"
        />
        <path d="M-32 529q119-47 240-5t224-8 244-22v84H-32Z" fill="#0d7791" opacity=".78" />
      </g>
      <g
        transform="translate(604 461)"
        fill="#298f81"
        stroke="#b0e5b3"
        strokeWidth="1.1"
        strokeLinejoin="round"
      >
        <path d="M0 0q-57-9-65-72 51 6 65 72Z" />
        <path d="M0 0q-14-56 14-98 26 42-14 98Z" fill="#52ad85" />
        <path d="M0 0q20-48 50-58-1 40-50 58Z" fill="#319f94" />
        <path d="M0 0q-29-21-51-56m51 56q13-31 14-82M0 0q26-16 40-42" fill="none" />
      </g>
    </>
  )
}

export function SeasonalScene({
  theme,
  placement = 'hero',
  paused = false,
}: {
  theme: SeasonalTheme
  placement?: 'hero' | 'sample'
  paused?: boolean
}) {
  return (
    <svg
      className="season-scene"
      data-seasonal-scene={theme}
      data-scene-placement={placement}
      data-motion-paused={paused || undefined}
      aria-hidden="true"
      focusable="false"
      viewBox={theme === 'christmas' ? '0 0 640 360' : '0 0 640 560'}
      preserveAspectRatio={theme === 'christmas' ? 'xMidYMid meet' : 'none'}
    >
      {theme === 'halloween' && <Halloween />}
      {theme === 'christmas' && <ChristmasScene />}
      {theme === 'summer' && <Summer />}
    </svg>
  )
}
