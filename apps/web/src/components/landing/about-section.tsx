import { CalendarHeart, MessageCircle, Users } from 'lucide-react'
import { useTranslation } from 'react-i18next'

import groupPhoto from '@/assets/group.jpg'
import { Card, CardContent } from '@/components/ui/card'
import { HowItWorks } from '@/components/landing/how-it-works'
import { Typography } from '@/components/ui/typography'

const features = [
  { key: 'social', icon: Users },
  { key: 'academic', icon: MessageCircle },
  { key: 'campus', icon: CalendarHeart },
] as const

function AboutSection() {
  const { t } = useTranslation()

  return (
    <section
      id="about"
      className="scroll-mt-20 bg-black px-4 py-16 sm:px-6 sm:py-20 lg:px-8"
      aria-labelledby="about-title"
    >
      <div className="mx-auto grid max-w-7xl items-center gap-12 lg:grid-cols-2 lg:gap-16">
        <div>
          <p className="mb-4 text-sm font-semibold uppercase tracking-[0.18em] text-vgu-orange">
            {t('about.eyebrow')}
          </p>
          <Typography id="about-title" variant="h2">
            {t('about.title')}
          </Typography>
          <Typography variant="lead" className="mt-5 max-w-2xl text-zinc-400">
            {t('about.subtitle')}
          </Typography>

          <div className="mt-9 grid gap-4">
            {features.map(({ key, icon: Icon }) => (
              <Card key={key} className="border-white/10 bg-zinc-900/70 shadow-lg">
                <CardContent className="flex items-start gap-4 p-5 sm:p-6">
                  <span
                    className="flex size-12 shrink-0 items-center justify-center rounded-xl bg-vgu-orange text-black"
                    aria-hidden="true"
                  >
                    <Icon className="size-6" />
                  </span>
                  <div>
                    <Typography variant="h3" className="text-xl">
                      {t(`about.${key}.title`)}
                    </Typography>
                    <p className="mt-2 text-base leading-7 text-zinc-400">
                      {t(`about.${key}.desc`)}
                    </p>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>

        <div className="relative mx-auto w-full max-w-2xl lg:max-w-none">
          <div className="absolute -inset-2 rounded-3xl bg-gradient-to-br from-vgu-orange to-vgu-orange-dark opacity-30 blur-xl" />
          <figure className="relative overflow-hidden rounded-2xl border border-orange-300/30 bg-zinc-950 p-3 shadow-2xl sm:p-5">
            <img
              src={groupPhoto}
              alt={t('about.imageAlt')}
              className="aspect-[3/2] w-full rounded-xl object-cover"
              loading="lazy"
            />
          </figure>
        </div>
      </div>
      <HowItWorks />
    </section>
  )
}

export { AboutSection }
