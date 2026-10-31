import { useRef, useState } from 'react'
import { CalendarHeart, Check, MessageCircle, Send, Sparkles, UserRound } from 'lucide-react'
import { useTranslation } from 'react-i18next'

import { Typography } from '@/components/ui/typography'
import { cn } from '@/lib/utils'

const steps = ['profile', 'discover', 'connect'] as const

function HowItWorks() {
  const { t } = useTranslation()
  const [active, setActive] = useState(0)
  const tabs = useRef<(HTMLButtonElement | null)[]>([])
  const step = steps[active]
  const label = (key: string) => t(`howItWorks.${key}`)

  return (
    <div className="landing-how" aria-labelledby="how-title">
      <p className="mb-4 text-sm font-semibold uppercase tracking-[0.18em] text-vgu-orange">
        {label('eyebrow')}
      </p>
      <Typography id="how-title" variant="h2" className="max-w-3xl">
        {label('title')}
      </Typography>
      <div className="landing-how-layout">
        <div className="landing-step-tabs" role="tablist" aria-labelledby="how-title">
          {steps.map((key, index) => (
            <button
              key={key}
              ref={(el) => {
                tabs.current[index] = el
              }}
              type="button"
              role="tab"
              id={`how-tab-${key}`}
              aria-controls="how-panel"
              aria-selected={active === index}
              tabIndex={active === index ? 0 : -1}
              onClick={() => setActive(index)}
              onKeyDown={(event) => {
                let next = index
                if (event.key === 'ArrowRight') next = (index + 1) % steps.length
                else if (event.key === 'ArrowLeft') next = (index + steps.length - 1) % steps.length
                else if (event.key === 'Home') next = 0
                else if (event.key === 'End') next = steps.length - 1
                else return
                event.preventDefault()
                setActive(next)
                tabs.current[next]?.focus()
              }}
              className={cn(
                'landing-step-tab flex min-h-16 items-center gap-3 rounded-xl border p-4 text-left font-semibold transition-colors duration-200 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-vgu-orange motion-reduce:transition-none',
                active === index
                  ? 'border-vgu-orange bg-vgu-orange/10 text-white'
                  : 'border-white/10 bg-zinc-900/60 text-zinc-300 hover:border-white/30',
              )}
            >
              <span
                aria-hidden="true"
                className={cn(
                  'flex size-8 shrink-0 items-center justify-center rounded-full text-sm',
                  active === index ? 'bg-vgu-orange text-black' : 'bg-white/10 text-zinc-300',
                )}
              >
                {index + 1}
              </span>
              {label(`${key}.title`)}
            </button>
          ))}
        </div>
        <div
          id="how-panel"
          role="tabpanel"
          aria-labelledby={`how-tab-${step}`}
          tabIndex={0}
          className="landing-step-panel rounded-2xl border border-white/10 bg-zinc-950 p-6 focus-visible:outline focus-visible:outline-2 focus-visible:outline-vgu-orange sm:p-10"
        >
          <div
            key={step}
            className="grid items-center gap-8 motion-safe:animate-[buddy-step-in_250ms_ease-out] xl:grid-cols-[0.8fr_1.2fr]"
          >
            <div>
              <Typography variant="h3">{label(`${step}.title`)}</Typography>
              <p className="mt-4 max-w-lg text-lg leading-8 text-zinc-300">
                {label(`${step}.desc`)}
              </p>
            </div>
            <figure className="min-w-0">
              <div className="space-y-4 rounded-xl border border-white/10 bg-zinc-900 p-5 sm:p-6">
                <div className="flex items-center gap-3 border-b border-white/10 pb-4">
                  <span className="flex size-12 shrink-0 items-center justify-center rounded-full bg-vgu-orange/15 text-vgu-orange">
                    <UserRound aria-hidden="true" />
                  </span>
                  <p className="font-semibold">
                    {step === 'profile' ? label('profile.title') : label('student')}
                  </p>
                </div>
                {step === 'profile' ? (
                  <dl className="grid gap-3">
                    {(['interests', 'languages', 'activities'] as const).map((key, index) => (
                      <div key={key} className="rounded-lg border border-white/10 p-3">
                        <dt className="text-sm text-zinc-400">{label(key)}</dt>
                        <dd className="mt-1 text-sm text-zinc-100">
                          {label(['interestExample', 'languageExample', 'activityExample'][index])}
                        </dd>
                      </div>
                    ))}
                  </dl>
                ) : step === 'discover' ? (
                  <div className="space-y-5">
                    <div className="flex flex-wrap items-center gap-2 text-vgu-orange">
                      <Sparkles className="size-5" aria-hidden="true" />
                      <span className="text-3xl font-bold">87%</span>
                      <span className="text-sm">{label('compatibility')}</span>
                    </div>
                    <p className="text-sm text-zinc-300">{label('interestExample')}</p>
                    <div className="grid gap-3 sm:grid-cols-2">
                      <span className="rounded-lg border border-white/20 px-3 py-3 text-center text-sm">
                        {label('viewProfile')}
                      </span>
                      <span className="flex items-center justify-center gap-2 rounded-lg bg-vgu-orange px-3 py-3 text-center text-sm font-semibold text-black">
                        <Send className="size-4 shrink-0" aria-hidden="true" />
                        {label('invite')}
                      </span>
                    </div>
                  </div>
                ) : (
                  <div className="space-y-4">
                    <div className="flex items-center gap-3 rounded-lg border border-vgu-orange/30 bg-vgu-orange/10 p-3">
                      <Check className="shrink-0 text-vgu-orange" aria-hidden="true" />
                      <div>
                        <p className="text-sm font-semibold">{label('accepted')}</p>
                        <p className="mt-1 text-sm text-zinc-300">{label('buddies')}</p>
                      </div>
                    </div>
                    <p className="flex items-center gap-3 rounded-lg border border-white/10 p-3 text-sm">
                      <MessageCircle
                        className="size-5 shrink-0 text-vgu-orange"
                        aria-hidden="true"
                      />
                      {label('chat')}
                    </p>
                    <p className="flex items-center gap-3 rounded-lg border border-white/10 p-3 text-sm">
                      <CalendarHeart
                        className="size-5 shrink-0 text-vgu-orange"
                        aria-hidden="true"
                      />
                      {label('events')}
                    </p>
                  </div>
                )}
              </div>
              <figcaption className="mt-3 text-xs leading-5 text-zinc-400">
                {label('illustration')}
              </figcaption>
            </figure>
          </div>
        </div>
      </div>
    </div>
  )
}

export { HowItWorks }
