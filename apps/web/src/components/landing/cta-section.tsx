import { useTranslation } from 'react-i18next'

import { Button } from '@/components/ui/button'
import { Typography } from '@/components/ui/typography'

/**
 * CTA Section
 *
 * Prompts students to take action ("Ready to Transform Your University Experience?")
 * with "Join the Community" (primary) and "Watch Demo" (secondary) action buttons.
 *
 * Navigation to registration or media modal is deferred to Auth Phase (AUTH-002)
 * to avoid speculative routing before the feature contracts exist.
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
        <Typography id="cta-title" variant="h2" className="text-3xl font-bold sm:text-4xl lg:text-5xl">
          {t('cta.title')}
        </Typography>

        <Typography variant="lead" className="mx-auto mt-6 max-w-2xl text-zinc-400">
          {t('cta.subtitle')}
        </Typography>

        <div className="mt-10 flex flex-col items-center justify-center gap-4 sm:flex-row sm:gap-5">
          <Button
            type="button"
            size="lg"
            className="w-full sm:w-auto"
          >
            {t('cta.join')}
          </Button>

          <Button
            type="button"
            variant="outline"
            size="lg"
            className="w-full sm:w-auto"
          >
            {t('cta.demo')}
          </Button>
        </div>
      </div>
    </section>
  )
}

export { CtaSection }
