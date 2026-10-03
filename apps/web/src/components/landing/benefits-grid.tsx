import { BookOpen, Building2, CalendarDays, Dumbbell, Globe, ShoppingBag } from 'lucide-react'
import { useTranslation } from 'react-i18next'

import { Card, CardContent } from '@/components/ui/card'
import { Typography } from '@/components/ui/typography'

/**
 * The six benefit cards are informational only.
 *
 * Navigation is intentionally omitted because:
 * - Legacy HTML pages (Merchandise, Calendar) have not been migrated.
 * - External VGU links (Library, Sports, International Office, Dormitory) are
 *   deferred until the routing/external-navigation strategy is confirmed.
 *
 * Links will be added once the corresponding routes or navigation strategy are
 * officially implemented and approved.
 */

const benefits = [
  { key: 'social', icon: ShoppingBag },
  { key: 'events', icon: CalendarDays },
  { key: 'academic', icon: BookOpen },
  { key: 'sports', icon: Dumbbell },
  { key: 'support', icon: Globe },
  { key: 'global', icon: Building2 },
] as const

function BenefitsGrid() {
  const { t } = useTranslation()

  return (
    <section
      id="features"
      className="bg-vgu-surface px-4 py-16 sm:px-6 sm:py-20 lg:px-8"
      aria-labelledby="features-title"
    >
      <div className="mx-auto max-w-7xl">
        <div className="mb-12 text-center sm:mb-16">
          <Typography id="features-title" variant="h2">
            {t('features.title')}
          </Typography>
          <Typography variant="lead" className="mx-auto mt-5 max-w-3xl text-zinc-400">
            {t('features.subtitle')}
          </Typography>
        </div>

        <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
          {benefits.map(({ key, icon: Icon }) => (
            <Card
              key={key}
              className="group border-white/10 bg-zinc-900/70 shadow-lg transition-[border-color,box-shadow] duration-300 ease-out hover:border-vgu-orange/50 hover:shadow-[0_8px_30px_rgba(255,103,13,0.12)] motion-reduce:transition-none"
            >
              <CardContent className="flex flex-col items-start gap-4 p-6 sm:p-7">
                <span
                  className="flex size-12 shrink-0 items-center justify-center rounded-xl bg-vgu-orange/10 text-vgu-orange transition-colors duration-300 group-hover:bg-vgu-orange group-hover:text-black motion-reduce:transition-none"
                  aria-hidden="true"
                >
                  <Icon className="size-6" />
                </span>

                <div>
                  <Typography variant="h3" className="text-xl">
                    {t(`features.${key}.title`)}
                  </Typography>
                  <p className="mt-2 text-base leading-7 text-zinc-400">
                    {t(`features.${key}.desc`)}
                  </p>
                </div>

                <ul className="mt-1 space-y-1.5" aria-label={t(`features.${key}.title`)}>
                  {(['item1', 'item2', 'item3'] as const).map((item) => (
                    <li key={item} className="flex items-center gap-2 text-sm text-zinc-500">
                      <span
                        className="size-1.5 shrink-0 rounded-full bg-vgu-orange/60"
                        aria-hidden="true"
                      />
                      {t(`features.${key}.${item}`)}
                    </li>
                  ))}
                </ul>
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    </section>
  )
}

export { BenefitsGrid }
