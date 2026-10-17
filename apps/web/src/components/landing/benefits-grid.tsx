import {
  BookOpen,
  Building2,
  CalendarDays,
  Dumbbell,
  ExternalLink,
  Globe,
  ShoppingBag,
} from 'lucide-react'
import { useTranslation } from 'react-i18next'

import { Card, CardContent } from '@/components/ui/card'
import { Typography } from '@/components/ui/typography'

// Official destinations confirmed by the owner on 2026-10-17.
const resources = [
  { key: 'social', icon: ShoppingBag, href: null },
  { key: 'events', icon: CalendarDays, href: null },
  { key: 'academic', icon: BookOpen, href: 'https://library.vgu.edu.vn/' },
  { key: 'sports', icon: Dumbbell, href: 'https://vgu.edu.vn/sports-complex' },
  { key: 'support', icon: Globe, href: 'https://vgu.edu.vn/international-office' },
  { key: 'global', icon: Building2, href: 'https://dorm.vgu.edu.vn/' },
] as const

function BenefitsGrid() {
  const { t } = useTranslation()

  return (
    <section
      id="features"
      className="scroll-mt-20 bg-vgu-surface px-4 py-16 sm:px-6 sm:py-20 lg:px-8"
      aria-labelledby="features-title"
    >
      <div className="mx-auto max-w-7xl">
        <div className="mb-12 text-center sm:mb-16">
          <p className="mb-4 text-sm font-semibold uppercase tracking-[0.18em] text-vgu-orange">
            {t('features.eyebrow')}
          </p>
          <Typography id="features-title" variant="h2">
            {t('features.title')}
          </Typography>
          <Typography variant="lead" className="mx-auto mt-5 max-w-3xl text-zinc-400">
            {t('features.subtitle')}
          </Typography>
        </div>

        <div className="grid auto-rows-fr grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3">
          {resources.map(({ key, icon: Icon, href }) => (
            <Card
              key={key}
              className="group min-w-0 border-white/10 bg-zinc-900/70 shadow-lg transition-[border-color,box-shadow] duration-300 hover:border-vgu-orange/50 hover:shadow-[0_8px_30px_rgba(255,103,13,0.12)] motion-reduce:transition-none"
            >
              <CardContent className="flex h-full flex-col items-start p-6 sm:p-7">
                <span
                  className="mb-6 flex size-12 shrink-0 items-center justify-center rounded-xl bg-vgu-orange/10 text-vgu-orange"
                  aria-hidden="true"
                >
                  <Icon className="size-6" />
                </span>
                <Typography variant="h3" className="text-xl">
                  {t(`features.${key}.title`)}
                </Typography>
                <p className="mb-6 mt-3 text-base leading-7 text-zinc-400">
                  {t(`features.${key}.desc`)}
                </p>
                {href ? (
                  <a
                    href={href}
                    aria-label={`${t('features.visit', { resource: t(`features.${key}.title`) })} ${t('features.newTab')}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="mt-auto inline-flex min-h-11 items-center gap-2 rounded-md py-2 text-sm font-semibold text-orange-300 underline-offset-4 hover:text-orange-200 hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-vgu-orange focus-visible:ring-offset-4 focus-visible:ring-offset-zinc-900"
                  >
                    {t('features.visit', { resource: t(`features.${key}.title`) })}
                    <ExternalLink aria-hidden="true" className="size-4 shrink-0" />
                    <span className="sr-only"> {t('features.newTab')}</span>
                  </a>
                ) : (
                  <p className="mt-auto border-t border-white/10 pt-4 text-sm text-zinc-400">
                    {t(key === 'social' ? 'features.merchPending' : 'features.recapPending')}
                  </p>
                )}
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    </section>
  )
}

export { BenefitsGrid }
