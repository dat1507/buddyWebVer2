import { useContext } from 'react'
import { ArrowDown, ArrowRight, Pause, Play, Sparkles, Users } from 'lucide-react'
import { LandingMotionContext } from '@/components/landing/landing-motion'
import { useTranslation } from 'react-i18next'
import { Link } from 'react-router'
import { HeroBackgroundSlideshow } from '@/components/landing/hero-background-slideshow'
import { Button } from '@/components/ui/button'
import { Typography } from '@/components/ui/typography'

function HeroSection() {
  const { t } = useTranslation()
  const { paused, toggle } = useContext(LandingMotionContext)
  return (
    <section id="home" className="landing-hero" aria-labelledby="hero-title">
      <div className="landing-shell landing-hero-grid">
        <div className="landing-hero-copy">
          <p className="landing-eyebrow">
            <span className="landing-dot" />
            {t('hero.communityLabel')}
          </p>
          <Typography id="hero-title" variant="h1">
            <span className="block">{t('hero.title1')}</span>
            <span className="landing-title-accent">{t('hero.title2')}</span>
          </Typography>
          <Typography variant="lead" className="landing-hero-description">
            {t('hero.subtitle')}
          </Typography>
          <div className="landing-hero-actions">
            <Button asChild size="lg" className="landing-primary rounded-full">
              <Link to="/register">
                {t('hero.joinCommunity')}
                <ArrowRight aria-hidden="true" />
              </Link>
            </Button>
            <a className="landing-text-link" href="#about">
              {t('hero.learnMore')}
              <ArrowDown aria-hidden="true" className="size-4" />
            </a>
          </div>
          <div className="landing-hero-note">
            <Users aria-hidden="true" className="size-5" />
            <p>{t('landingRedesign.heroNote')}</p>
          </div>
          <button
            type="button"
            className="landing-motion-toggle"
            onClick={toggle}
            aria-pressed={paused}
          >
            {paused ? (
              <Play aria-hidden="true" className="size-4" />
            ) : (
              <Pause aria-hidden="true" className="size-4" />
            )}
            {t(paused ? 'landingRedesign.resumeMotion' : 'landingRedesign.pauseMotion')}
          </button>
        </div>
        <div className="landing-hero-visual">
          <div className="landing-campus-photo">
            <HeroBackgroundSlideshow />
            <div className="landing-photo-shade" aria-hidden="true" />
            <div className="landing-photo-caption">
              <span className="landing-eyebrow">VIETNAMESE–GERMAN UNIVERSITY</span>
              <p>{t('landingRedesign.photoCaption')}</p>
            </div>
          </div>
          <div className="landing-hello">
            <Sparkles aria-hidden="true" className="size-6" />
            <span>{t('landingRedesign.hello')}</span>
          </div>
          <a className="landing-campus-tag" href="#features">
            <span className="landing-dot" />
            {t('features.eyebrow')}
            <ArrowRight aria-hidden="true" className="size-4" />
          </a>
        </div>
      </div>
      <div className="landing-ribbon" aria-hidden="true">
        <span>VGU BUDDY PROGRAM</span>
        <span>✳</span>
        <span>{t('landingRedesign.ribbon')}</span>
        <span>✳</span>
        <span>VGU BUDDY PROGRAM</span>
      </div>
    </section>
  )
}
export { HeroSection }
