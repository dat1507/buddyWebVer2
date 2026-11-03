import { ArrowLeft, CalendarDays, Shirt, ShoppingBag, Sparkles } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { Link } from 'react-router'

import { Button } from '@/components/ui/button'
import { Typography } from '@/components/ui/typography'

function CommunityComingSoonPage({ feature }: { feature: 'recap' | 'merchandise' }) {
  const { t } = useTranslation()
  const Icon = feature === 'recap' ? CalendarDays : ShoppingBag

  if (feature === 'merchandise')
    return (
      <main className="community-surface merchandise-page" aria-labelledby="coming-soon-title">
        <div className="merchandise-shell">
          <div className="merchandise-copy">
            <p className="merchandise-eyebrow">VGU BUDDY</p>
            <p className="merchandise-badge">
              <Sparkles aria-hidden="true" className="size-4" />
              {t('features.merchPending')}
            </p>
            <Typography id="coming-soon-title" variant="h1">
              {t('communityComingSoon.merchandise.title')}
            </Typography>
            <p className="merchandise-description">
              {t('communityComingSoon.merchandise.description')}
            </p>
            <Button
              asChild
              variant="outline"
              className="min-h-12 gap-2 rounded-full motion-reduce:transition-none"
            >
              <Link to="/#events">
                <ArrowLeft aria-hidden="true" className="size-4" />
                {t('communityComingSoon.back')}
              </Link>
            </Button>
          </div>
          <div className="merchandise-art" aria-hidden="true">
            <div className="merchandise-orbit" />
            <div className="merchandise-shirt">
              <Shirt strokeWidth={1.15} />
              <span>BUDDY</span>
            </div>
            <div className="merchandise-bag">
              <ShoppingBag strokeWidth={1.15} />
              <span>
                VGU
                <br />
                BUDDY
              </span>
            </div>
            <span className="merchandise-star">✦</span>
            <span className="merchandise-art-note">MEET · CONNECT · BELONG</span>
          </div>
        </div>
      </main>
    )

  return (
    <main
      className="flex min-h-[60vh] items-center justify-center px-4 py-16 sm:px-6 sm:py-20"
      aria-labelledby="coming-soon-title"
    >
      <div className="mx-auto max-w-3xl text-center">
        <Icon aria-hidden="true" className="mx-auto mb-6 size-12 text-vgu-orange" />
        <p className="mb-4 text-sm font-semibold uppercase tracking-[0.18em] text-orange-300">
          {t('features.merchPending')}
        </p>
        <Typography id="coming-soon-title" variant="h1">
          {t(`communityComingSoon.${feature}.title`)}
        </Typography>
        <p className="mx-auto mb-8 mt-5 max-w-2xl text-lg leading-8 text-zinc-400">
          {t(`communityComingSoon.${feature}.description`)}
        </p>
        <Button asChild variant="outline" className="min-h-11 gap-2 motion-reduce:transition-none">
          <Link to="/#events">
            <ArrowLeft aria-hidden="true" className="size-4" />
            {t('communityComingSoon.back')}
          </Link>
        </Button>
      </div>
    </main>
  )
}

export { CommunityComingSoonPage }
