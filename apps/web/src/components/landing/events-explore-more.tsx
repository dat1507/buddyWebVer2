import { ArrowRight, CalendarDays, ShoppingBag } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { Link } from 'react-router'

import { Card, CardContent } from '@/components/ui/card'

const features = [
  { key: 'recap', href: '/events/recap', icon: CalendarDays },
  { key: 'merchandise', href: '/merchandise', icon: ShoppingBag },
] as const

function EventsExploreMore() {
  const { t } = useTranslation()

  return (
    <div
      role="region"
      aria-labelledby="explore-more-title"
      className="bg-vgu-surface px-4 pb-16 sm:px-6 sm:pb-20 lg:px-8"
    >
      <div className="mx-auto max-w-4xl border-t border-white/10 pt-10">
        <h2 id="explore-more-title" className="text-center text-2xl font-bold text-zinc-100">
          {t('eventsShowcase.title')}
        </h2>
        <p className="mt-3 text-center text-base leading-7 text-zinc-400">
          {t('eventsShowcase.description')}
        </p>
        <div className="mt-8 grid auto-rows-fr gap-6 sm:grid-cols-2">
          {features.map(({ key, href, icon: Icon }) => (
            <Card
              key={key}
              className="min-w-0 border-white/10 bg-zinc-900/70 shadow-lg transition-[border-color,box-shadow] hover:border-vgu-orange/50 hover:shadow-xl motion-reduce:transition-none"
            >
              <CardContent className="flex h-full flex-col items-start p-6">
                <Icon aria-hidden="true" className="mb-4 size-6 text-vgu-orange" />
                <h3 className="text-xl font-bold text-zinc-100">
                  {t(`eventsShowcase.${key}.title`)}
                </h3>
                <p className="mt-3 text-base leading-7 text-zinc-400">
                  {t(`eventsShowcase.${key}.description`)}
                </p>
                {key === 'merchandise' && (
                  <p className="mt-3 text-sm font-medium text-orange-300">
                    {t('features.merchPending')}
                  </p>
                )}
                <Link
                  to={href}
                  className="mt-auto inline-flex min-h-11 items-center gap-2 rounded-md pt-5 text-sm font-semibold text-orange-300 underline-offset-4 hover:text-orange-200 hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-vgu-orange focus-visible:ring-offset-4 focus-visible:ring-offset-zinc-900"
                >
                  {t(`eventsShowcase.${key}.action`)}
                  <ArrowRight aria-hidden="true" className="size-4 shrink-0" />
                </Link>
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    </div>
  )
}

export { EventsExploreMore }
