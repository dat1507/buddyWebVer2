import { useTranslation } from 'react-i18next'
import { Link } from 'react-router'

import { Button } from '@/components/ui/button'
import { Typography } from '@/components/ui/typography'

/**
 * CTA Section
 *
 * Prompts students to take action ("Ready to Transform Your University Experience?")
 * with a centered "Join the Community" action that routes students to registration.
 */
function CtaSection() {
  const { t } = useTranslation()

  return (
    <section
      id="cta"
      className="relative overflow-hidden bg-vgu-surface px-4 py-20 sm:px-6 sm:py-24 lg:px-8"
      aria-labelledby="cta-title"
    >
      {/* Background ambient glow */}
      <div
        className="pointer-events-none absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 size-96 rounded-full bg-vgu-orange/10 blur-3xl sm:size-[32rem]"
        aria-hidden="true"
      />

      <div className="relative mx-auto max-w-4xl text-center">
        <Typography
          id="cta-title"
          variant="h2"
          className="text-3xl font-bold sm:text-4xl lg:text-5xl"
        >
          {t('cta.title')}
        </Typography>

        <Typography variant="lead" className="mx-auto mt-6 max-w-2xl text-zinc-400">
          {t('cta.subtitle')}
        </Typography>

        <div className="mt-10 flex justify-center">
          <Button asChild size="lg" className="w-full sm:w-auto">
            <Link to="/register">{t('cta.join')}</Link>
          </Button>
        </div>
      </div>
    </section>
  )
}

export { CtaSection }
