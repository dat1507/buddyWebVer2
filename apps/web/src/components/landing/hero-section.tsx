import { useTranslation } from 'react-i18next'

import { HeroBackgroundSlideshow } from '@/components/landing/hero-background-slideshow'
import { Button } from '@/components/ui/button'
import { Typography } from '@/components/ui/typography'

function HeroSection() {
  const { t } = useTranslation()

  return (
    <section
      id="home"
      className="hero-gradient relative flex min-h-[calc(100svh-4rem)] items-center overflow-hidden selection:bg-vgu-orange selection:text-vgu-black"
      aria-labelledby="hero-title"
    >
      <HeroBackgroundSlideshow />
      <div
        className="pointer-events-none absolute inset-0 z-[1] bg-gradient-to-r from-black/85 via-black/65 to-black/45"
        aria-hidden="true"
      />
      <div className="relative z-10 mx-auto w-full max-w-7xl px-4 py-16 sm:px-6 sm:py-20 lg:px-8">
        <div className="max-w-3xl">
          <div className="space-y-8 rounded-3xl bg-black/20 p-6 shadow-2xl backdrop-blur-[2px] sm:p-8">
            <Typography
              id="hero-title"
              variant="h1"
              className="drop-shadow-[0_0_18px_rgba(255,103,13,0.2)]"
            >
              <span className="block motion-safe:animate-slide-in-left">{t('hero.title1')}</span>
              <span className="block text-vgu-orange motion-safe:animate-slide-in-left motion-safe:[animation-delay:200ms]">
                {t('hero.title2')}
              </span>
            </Typography>

            <Typography
              variant="lead"
              className="max-w-2xl text-zinc-300 motion-safe:animate-fade-in-up motion-safe:[animation-delay:400ms]"
            >
              {t('hero.subtitle')}
            </Typography>

            <div className="motion-safe:animate-fade-in-up motion-safe:[animation-delay:600ms]">
              <Button asChild variant="outline" size="lg">
                <a href="#about">{t('hero.learnMore')}</a>
              </Button>
            </div>
          </div>
        </div>
      </div>
    </section>
  )
}

export { HeroSection }
