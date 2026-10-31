import { useEffect, useState } from 'react'
import '@/styles/landing.css'
import { useTranslation } from 'react-i18next'
import { useLocation } from 'react-router'

import { AboutSection } from '@/components/landing/about-section'
import { BenefitsGrid } from '@/components/landing/benefits-grid'
import { CtaSection } from '@/components/landing/cta-section'
import { EventsSlider } from '@/components/landing/events-slider'
import { EventsExploreMore } from '@/components/landing/events-explore-more'
import { HeroSection } from '@/components/landing/hero-section'
import { LiveEventsSection } from '@/components/landing/live-events-section'
import { LandingMotionContext } from '@/components/landing/landing-motion'
import { TestimonialsMarquee } from '@/components/landing/testimonials-marquee'
import type { EventSliderLocale } from '@/features/events/event-slider'
import { getStaticUpcomingEvents } from '@/features/events/data/static-upcoming-events'
import { publicEventsEnabled } from '@/config/launch-scope'

function LandingPage() {
  const [paused, setPaused] = useState(false)
  const { t, i18n } = useTranslation()
  const { state, hash } = useLocation()

  useEffect(() => {
    if (!['#about', '#features', '#events'].includes(hash)) return
    const frame = requestAnimationFrame(() => {
      document.getElementById(hash.slice(1))?.scrollIntoView()
    })
    return () => cancelAnimationFrame(frame)
  }, [hash])
  const eventLocale: EventSliderLocale = i18n.resolvedLanguage?.startsWith('de') ? 'de' : 'en'

  return (
    <LandingMotionContext value={{ paused, toggle: () => setPaused((previous) => !previous) }}>
      <main className="landing-page">
        {state?.authNotice === 'adminDenied' ? (
          <p
            role="alert"
            className="border-b border-amber-300/25 bg-amber-400/10 px-4 py-3 text-sm text-amber-100"
          >
            {t('auth.adminLogin.denied')}
          </p>
        ) : null}
        <HeroSection />
        {publicEventsEnabled ? (
          <LiveEventsSection locale={eventLocale} />
        ) : (
          <EventsSlider events={getStaticUpcomingEvents(eventLocale)} />
        )}
        <EventsExploreMore />
        <AboutSection />
        <BenefitsGrid />
        <TestimonialsMarquee />
        <CtaSection />
      </main>
    </LandingMotionContext>
  )
}

export { LandingPage }
