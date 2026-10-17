import { ExternalLink } from 'lucide-react'
import { useTranslation } from 'react-i18next'

import libraryImage from '@/assets/campus-resources/library.webp'
import sportsImage from '@/assets/campus-resources/sports-hall.webp'
import officeImage from '@/assets/campus-resources/international-office.webp'
import dormitoryImage from '@/assets/campus-resources/dormitory.webp'

import { Card, CardContent } from '@/components/ui/card'
import { Typography } from '@/components/ui/typography'

// Official destinations confirmed by the owner on 2026-10-17.
const resources = [
  {
    key: 'academic',
    image: libraryImage,
    width: 1201,
    height: 800,
    position: '50% 50%',
    href: 'https://library.vgu.edu.vn/',
  },
  {
    key: 'sports',
    image: sportsImage,
    width: 1440,
    height: 810,
    position: '50% 50%',
    href: 'https://vgu.edu.vn/sports-complex',
  },
  {
    key: 'support',
    image: officeImage,
    width: 1440,
    height: 846,
    position: '50% 40%',
    href: 'https://vgu.edu.vn/international-office',
  },
  {
    key: 'global',
    image: dormitoryImage,
    width: 1440,
    height: 959,
    position: '50% 65%',
    href: 'https://dorm.vgu.edu.vn/',
  },
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

        <div className="grid auto-rows-fr grid-cols-1 gap-6 sm:grid-cols-2">
          {resources.map(({ key, image, width, height, position, href }) => (
            <Card
              key={key}
              className="group flex min-w-0 flex-col overflow-hidden border-white/10 bg-zinc-900/70 shadow-lg transition-[border-color,box-shadow] duration-300 hover:border-vgu-orange/50 hover:shadow-[0_8px_30px_rgba(255,103,13,0.12)] motion-reduce:transition-none"
            >
              <div className="aspect-video shrink-0 overflow-hidden bg-zinc-800">
                <img
                  src={image}
                  alt={t(`features.${key}.imageAlt`)}
                  width={width}
                  height={height}
                  loading="lazy"
                  decoding="async"
                  className="h-full w-full object-cover"
                  style={{ objectPosition: position }}
                />
              </div>
              <CardContent className="flex flex-1 flex-col items-start p-6 sm:p-7">
                <Typography variant="h3" className="text-xl">
                  {t(`features.${key}.title`)}
                </Typography>
                <p className="mb-6 mt-3 text-base leading-7 text-zinc-400">
                  {t(`features.${key}.desc`)}
                </p>
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
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    </section>
  )
}

export { BenefitsGrid }
