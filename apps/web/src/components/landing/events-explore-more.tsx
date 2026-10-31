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
      className="landing-explore -mt-4 bg-vgu-surface px-4 pb-16 sm:-mt-6 sm:px-6 sm:pb-20 lg:px-8"
    >
      <div className="mx-auto max-w-7xl">
        <h2 id="explore-more-title" className="text-center text-2xl font-bold text-zinc-100">
          {t('eventsShowcase.title')}
        </h2>
        <p className="mt-3 text-center text-base leading-7 text-zinc-400">
          {t('eventsShowcase.description')}
        </p>
        <div className="landing-explore-grid mt-8 grid auto-rows-fr gap-6 sm:grid-cols-2 lg:gap-8">
          {features.map(({ key, href, icon: Icon }) => (
            <Card
              key={key}
              className="min-w-0 border-white/10 bg-zinc-900/70 shadow-lg transition-[border-color,box-shadow] duration-200 hover:border-vgu-orange/50 hover:shadow-xl motion-reduce:transition-none"
            >
              <CardContent className="flex h-full flex-col items-start p-6 sm:p-7 lg:min-h-72 lg:p-8 xl:p-10">
                <div className="flex items-center gap-4">
                  <Icon aria-hidden="true" className="size-9 shrink-0 text-vgu-orange lg:size-10" />
                  <h3 className="text-xl font-bold text-zinc-100">
                    {t(`eventsShowcase.${key}.title`)}
                  </h3>
                </div>
                <p className="mt-4 text-base leading-7 text-zinc-400">
                  {t(`eventsShowcase.${key}.description`)}
                </p>
                <div className="mt-auto flex min-h-24 w-full flex-col items-start gap-x-4 gap-y-2 pt-6 lg:min-h-0 lg:flex-row lg:items-center lg:justify-between">
                  <Link
                    to={href}
                    className="inline-flex min-h-11 items-center gap-2 rounded-md text-sm font-semibold text-orange-300 underline-offset-4 hover:text-orange-200 hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-vgu-orange focus-visible:ring-offset-4 focus-visible:ring-offset-zinc-900"
                  >
                    {t(`eventsShowcase.${key}.action`)}
                    <ArrowRight aria-hidden="true" className="size-4 shrink-0" />
                  </Link>
                  {key === 'merchandise' && (
                    <span className="text-sm font-medium text-orange-300">
                      {t('features.merchPending')}
                    </span>
                  )}
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    </div>
  )
}

export { EventsExploreMore }
