import { useTranslation } from 'react-i18next'

import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Typography } from '@/components/ui/typography'

const facebookPageUrl = 'https://www.facebook.com/VGUBuddyProgram'

function HeroSection() {
  const { t } = useTranslation()

  return (
    <section
      id="home"
      className="hero-gradient relative flex min-h-[calc(100svh-4rem)] items-center overflow-hidden selection:bg-vgu-orange selection:text-vgu-black"
      aria-labelledby="hero-title"
    >
      <div className="relative z-10 mx-auto w-full max-w-7xl px-4 py-16 sm:px-6 sm:py-20 lg:px-8">
        <div className="grid items-center gap-12 lg:grid-cols-2">
          <div className="space-y-8">
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

          <a
            href={facebookPageUrl}
            target="_blank"
            rel="noreferrer"
            className="block rounded-2xl focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-orange-500 focus-visible:ring-offset-4 focus-visible:ring-offset-black motion-safe:animate-slide-in-right motion-safe:[animation-delay:300ms]"
            aria-label={`${t('hero.cardTitle')} — Facebook`}
          >
            <Card
              variant="interactive"
              className="border-white/10 bg-zinc-900/80 shadow-2xl backdrop-blur-sm"
            >
              <CardHeader className="items-center px-6 pt-8 text-center sm:px-8">
                <div
                  className="mb-3 flex justify-center -space-x-4 motion-safe:animate-fade-in-scale motion-safe:[animation-delay:500ms]"
                  aria-hidden="true"
                >
                  <span className="flex size-16 items-center justify-center rounded-full border-4 border-zinc-900 bg-vgu-orange text-2xl">
                    🤝
                  </span>
                  <span className="flex size-16 items-center justify-center rounded-full border-4 border-zinc-900 bg-vgu-orange-light text-2xl">
                    🌏
                  </span>
                  <span className="flex size-16 items-center justify-center rounded-full border-4 border-zinc-900 bg-vgu-orange-dark text-2xl">
                    🎓
                  </span>
                </div>
                <CardTitle className="motion-safe:animate-fade-in-up motion-safe:[animation-delay:600ms]">
                  {t('hero.cardTitle')}
                </CardTitle>
              </CardHeader>
              <CardContent className="px-6 pb-8 text-center sm:px-8">
                <CardDescription className="text-base leading-7 text-zinc-400 motion-safe:animate-fade-in-up motion-safe:[animation-delay:700ms]">
                  {t('hero.cardSubtitle')}
                </CardDescription>
              </CardContent>
            </Card>
          </a>
        </div>
      </div>
    </section>
  )
}

export { HeroSection }
