/** Original vector artwork. All motion is controlled by SeasonalScene's pause boundary. */
export function ChristmasScene() {
  return (
    <>
      <path d="M0 218Q90 175 180 220T360 212 640 196V360H0Z" fill="#dceef5" />
      <path d="M0 290Q130 245 270 292T640 270V360H0Z" fill="#f8fcff" />
      <ellipse cx="342" cy="321" rx="235" ry="20" fill="#bad5e2" opacity=".4" />
      {/* A single string connects the warm bulbs into the winter vignette. */}
      <path d="M20 22Q320 118 620 22" fill="none" stroke="#79929e" strokeWidth="2" />
      {[58, 124, 190, 256, 322, 388, 454, 520, 586].map((x, i) => {
        const y = 24 + 47 * (1 - ((x - 320) / 300) ** 2)
        return (
          <g key={x} transform={`translate(${x} ${y})`}>
            <path d="M0 0v9" stroke="#79929e" strokeWidth="2" />
            <g className={`christmas-bulb christmas-bulb-${i % 3}`}>
              <circle cy="16" r="15" fill="#edb95a" opacity=".14" />
              <ellipse cy="16" rx="5" ry="8" fill="#ffe4a2" stroke="#ba8742" />
              <path d="M-2 13v5" stroke="#fffdf5" strokeWidth="2" strokeLinecap="round" />
            </g>
          </g>
        )
      })}
      {/* Frosted trees give the little hearth a snowy woodland setting. */}
      <g fill="#a8c6d3" stroke="#f8fcff" strokeWidth="5" strokeLinejoin="round">
        <path d="m76 125-36 65h19l-34 55h29l-31 49h106l-31-49h26l-32-55h20Z" />
        <path d="m567 131-31 57h16l-29 49h23l-26 44h94l-28-44h22l-28-49h16Z" />
      </g>
      {/* Snow-capped stone fireplace, brass candles, garland and a wool stocking. */}
      <g data-christmas-art="fireplace">
        <path d="M291 142h166v170H291Z" fill="#b9ced7" />
        <path d="M300 150h148v158H300Z" fill="#dce8ec" />
        <path
          d="M302 184h144m-144 36h144m-144 36h144M326 150v34m88-34v34m-59 0v36m-28 0v36m88-36v36"
          stroke="#bbd0d9"
          strokeWidth="2"
        />
        <path
          d="M326 308v-63a48 48 0 0 1 96 0v63Z"
          fill="#3e4654"
          stroke="#aabfc9"
          strokeWidth="7"
        />
        <ellipse
          className="christmas-glow"
          cx="374"
          cy="270"
          rx="45"
          ry="38"
          fill="#f6b45d"
          opacity=".3"
        />
        <path
          d="m344 295 56-5m-53-4 51 13"
          stroke="#73534b"
          strokeWidth="9"
          strokeLinecap="round"
        />
        <g className="christmas-flame">
          <path
            d="M352 289c-20-23 15-33 12-60 23 19 7 28 19 33 8-7 10-15 9-22 32 31 11 59-15 59-10 0-18-3-25-10Z"
            fill="#e9a04c"
          />
          <path d="M365 290c-9-12 7-20 9-36 14 15 9 20 17 24 7 15-16 25-26 12Z" fill="#ffe2a0" />
        </g>
        <rect x="280" y="133" width="188" height="17" rx="5" fill="#8ba9b8" />
        <path d="M282 133q20-10 43-3t45-1 47 1 49 1v8H282Z" fill="#fff" />
        <rect x="280" y="306" width="188" height="13" rx="5" fill="#9eb9c7" />
        <path
          d="M297 151q77 34 152 0"
          fill="none"
          stroke="#6f9393"
          strokeWidth="7"
          strokeLinecap="round"
        />
        <g fill="#9d4355">
          <circle cx="330" cy="165" r="4" />
          <circle cx="373" cy="174" r="4" />
          <circle cx="418" cy="165" r="4" />
        </g>
        <path d="M421 168h17v30q-2 14-21 11-13-5-2-14l6-4Z" fill="#9d4355" />
        <path d="M419 168h21v8h-21Z" fill="#fff9ee" />
        <g fill="#fff2ce" stroke="#c5a165">
          <rect x="308" y="105" width="9" height="26" rx="2" />
          <rect x="432" y="109" width="9" height="22" rx="2" />
        </g>
        <g fill="#edb95a">
          <path d="M312 104q-7-6 1-14 7 10-1 14Z" />
          <path d="M436 108q-6-6 1-13 6 9-1 13Z" />
        </g>
      </g>
      {/* Santa: rounded burgundy coat, white beard, mittens and boots. */}
      <g data-christmas-art="santa">
        <path d="M183 282v26h-24q-9 12 6 14h34v-40m36 0v26h23q10 12-5 14h-34v-40" fill="#394a59" />
        <path
          d="M169 221q-15 12-22 42l15 9 19-29m51-22q20 6 29 30l-14 11-23-24"
          fill="#9d4355"
          stroke="#83374c"
          strokeWidth="3"
          strokeLinecap="round"
        />
        <ellipse cx="150" cy="269" rx="11" ry="13" fill="#faf6ea" />
        <ellipse cx="254" cy="257" rx="11" ry="13" fill="#faf6ea" />
        <path d="M172 221q31-18 60 0l16 72q-46 17-90 0Z" fill="#a44a5e" />
        <path d="M199 227v66m-38 0q42 13 84 0" fill="none" stroke="#fff8ec" strokeWidth="11" />
        <path d="M166 269q38 10 74 0" fill="none" stroke="#394a59" strokeWidth="12" />
        <rect x="194" y="267" width="18" height="14" rx="2" fill="#eac580" />
        <rect x="199" y="271" width="8" height="6" fill="#394a59" />
        <circle cx="203" cy="195" r="33" fill="#f0c3a4" />
        <path
          d="M171 191q4 38 32 51 31-15 33-51-9 18-19 11-14 11-28 0-12 7-18-11Z"
          fill="#fffbf2"
        />
        <ellipse cx="203" cy="203" rx="8" ry="6" fill="#e4a58c" />
        <path d="M188 190h2m26 0h2" stroke="#394a59" strokeWidth="3" strokeLinecap="round" />
        <path d="M175 172q7-41 42-43 26 0 28 24-18-15-23 19Z" fill="#9d4355" />
        <path d="M174 174q29-10 57 0" stroke="#fffbf2" strokeWidth="12" strokeLinecap="round" />
        <circle cx="246" cy="153" r="10" fill="#fffbf2" />
      </g>
      <g data-christmas-art="gifts">
        <rect x="476" y="271" width="60" height="45" rx="4" fill="#a44a5e" />
        <rect x="472" y="264" width="68" height="12" rx="3" fill="#bc6674" />
        <path
          d="M506 265v51m0-51c-34-1-24-25-10-13l10 13c34-1 24-25 10-13Z"
          fill="none"
          stroke="#f3d59b"
          strokeWidth="5"
          strokeLinejoin="round"
        />
        <rect x="538" y="290" width="40" height="28" rx="3" fill="#edcea0" />
        <path
          d="M557 289v29m-19-22h40m-21-7q-21-19-16-3l16 3q23-19 17-3Z"
          fill="none"
          stroke="#9b6670"
          strokeWidth="4"
        />
      </g>
      <g fill="#fff" stroke="#91b7cd" strokeWidth="1.3">
        {[0, 1].map((layer) => (
          <g key={layer} className={`christmas-snow christmas-snow-${layer}`}>
            {Array.from({ length: 16 }, (_, i) => {
              const x = 24 + ((i * 113 + layer * 49) % 590)
              const y = 10 + ((i * 67 + layer * 31) % 245)
              return i % 4 === 0 ? (
                <path
                  key={i}
                  className={i > 7 ? 'christmas-snow-extra' : undefined}
                  d={`M${x - 5} ${y}h10m-5-5v10m-4-9 8 8m-8 0 8-8`}
                />
              ) : (
                <circle
                  key={i}
                  className={i > 7 ? 'christmas-snow-extra' : undefined}
                  cx={x}
                  cy={y}
                  r={layer ? 2.4 : 1.5}
                  stroke="none"
                />
              )
            })}
          </g>
        ))}
      </g>
    </>
  )
}
