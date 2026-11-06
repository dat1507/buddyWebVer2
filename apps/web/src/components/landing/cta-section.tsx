import { ArrowUpRight } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { Link } from 'react-router'

import { Button } from '@/components/ui/button'
import { Typography } from '@/components/ui/typography'

function CtaSection() {
  const { t } = useTranslation()
  return (
    <section id="cta" className="landing-cta px-4 sm:px-6 lg:px-8" aria-labelledby="cta-title">
      <div className="landing-cta-card mx-auto max-w-7xl">
        <div className="landing-cta-copy">
          <p className="landing-eyebrow">{t('cta.eyebrow')}</p>
          <Typography id="cta-title" variant="h2">
            {t('cta.title')}
          </Typography>
          <Typography variant="lead">{t('cta.subtitle')}</Typography>
          <Button asChild size="lg" className="landing-primary mt-8 w-full gap-3 sm:w-auto">
            <Link to="/register">
              {t('cta.join')}
              <ArrowUpRight aria-hidden="true" className="size-5" />
            </Link>
          </Button>
        </div>
      </div>
    </section>
  )
}
export { CtaSection }
