import { AboutSection } from '@/components/landing/about-section'
import { BenefitsGrid } from '@/components/landing/benefits-grid'
import { CtaSection } from '@/components/landing/cta-section'
import { EventsSlider } from '@/components/landing/events-slider'
import { HeroSection } from '@/components/landing/hero-section'
import { TestimonialsMarquee } from '@/components/landing/testimonials-marquee'

function LandingPage() {
  return (
    <main>
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
