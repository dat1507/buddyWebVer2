import { CalendarHeart, MessageCircle, Users } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import groupPhoto from '@/assets/group.jpg'
import { HowItWorks } from '@/components/landing/how-it-works'
import { Typography } from '@/components/ui/typography'
const features = [
  { key: 'social', icon: Users },
  { key: 'academic', icon: MessageCircle },
  { key: 'campus', icon: CalendarHeart },
] as const
function AboutSection() {
  const { t } = useTranslation()
  return (
    <section id="about" className="landing-about scroll-mt-20" aria-labelledby="about-title">
      <div className="landing-shell">
        <div className="landing-section-intro">
          <div>
            <p className="landing-eyebrow">{t('about.eyebrow')}</p>
            <Typography id="about-title" variant="h2">
              {t('about.title')}
            </Typography>
          </div>
          <Typography variant="lead">{t('about.subtitle')}</Typography>
        </div>
        <div className="landing-about-grid">
          <figure className="landing-group-photo">
            <img
              src={groupPhoto}
              alt={t('about.imageAlt')}
              width="2048"
              height="1365"
              loading="lazy"
              decoding="async"
            />
            <figcaption>
              <Users aria-hidden="true" className="size-5" />
              {t('landingRedesign.together')}
            </figcaption>
          </figure>
          <div className="landing-values">
            {features.map(({ key, icon: Icon }, index) => (
              <article key={key} className="landing-value">
                <span className="landing-value-icon">
                  <Icon aria-hidden="true" className="size-6" />
                </span>
                <div>
                  <span className="landing-value-number" aria-hidden="true">
                    0{index + 1}
                  </span>
                  <Typography variant="h3">{t(`about.${key}.title`)}</Typography>
                  <p>{t(`about.${key}.desc`)}</p>
                </div>
              </article>
            ))}
          </div>
        </div>
        <HowItWorks />
      </div>
    </section>
  )
}
export { AboutSection }
