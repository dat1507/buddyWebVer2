import { useTranslation } from 'react-i18next'
import { useLocation } from 'react-router'

import { AboutSection } from '@/components/landing/about-section'
import { BenefitsGrid } from '@/components/landing/benefits-grid'
import { CtaSection } from '@/components/landing/cta-section'
import { EventsSlider } from '@/components/landing/events-slider'
import { HeroSection } from '@/components/landing/hero-section'
import { TestimonialsMarquee } from '@/components/landing/testimonials-marquee'

function LandingPage() {
  const { t } = useTranslation()
  const { state } = useLocation()
  return (
    <main>
      {state?.authNotice === 'adminDenied' ? (
        <p
          role="alert"
          className="border-b border-amber-300/25 bg-amber-400/10 px-4 py-3 text-sm text-amber-100"
        >
          {t('auth.adminLogin.denied')}
        </p>
      ) : null}
      <HeroSection />
      <EventsSlider />
      <AboutSection />
      <BenefitsGrid />
      <TestimonialsMarquee />
      <CtaSection />
    </main>
  )
}

export { LandingPage }
