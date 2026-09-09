import { AboutSection } from '@/components/landing/about-section'
import { EventsSlider } from '@/components/landing/events-slider'
import { HeroSection } from '@/components/landing/hero-section'

function LandingPage() {
  return (
    <main>
      <HeroSection />
      <EventsSlider />
      <AboutSection />
    </main>
  )
}

export { LandingPage }
