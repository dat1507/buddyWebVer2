import { useQuery } from '@tanstack/react-query'
import { ArrowUpRight, Camera, Images } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { Link } from 'react-router'
import { publicEventsEnabled } from '@/config/launch-scope'
import { MerchandiseArtwork } from '@/features/merchandise/merchandise-artwork'
import { RecapImage } from '@/features/recaps/recap-photo'
import { fetchRecaps } from '@/features/recaps/recaps'
import '@/features/recaps/recaps.css'

function MemoryArtwork() {
  return (
    <span className="explore-memory-art" aria-hidden="true">
      <span className="explore-memory-print explore-memory-print-back">
        <Images strokeWidth={1} />
      </span>
      <span className="explore-memory-print">
        <Camera strokeWidth={1} />
        <span>VGU BUDDY</span>
      </span>
    </span>
  )
}

function EventsExploreMore() {
  const { t } = useTranslation()
  // Share the public gallery cache and its canonical newest-first order.
  const query = useQuery({
    queryKey: ['recaps', 1, ''],
    queryFn: ({ signal }) => fetchRecaps(1, '', false, signal),
    enabled: publicEventsEnabled,
    staleTime: 30_000,
    retry: 1,
  })
  const latest = query.data?.items.find((recap) => recap.status === 'PUBLISHED')
  const photo = latest?.photos.find((item) => item.id === latest.thumbnail_id) ?? latest?.photos[0]
  return (
    <div
      role="region"
      aria-labelledby="explore-more-title"
      className="landing-explore px-4 sm:px-6 lg:px-8"
    >
      <div className="mx-auto max-w-7xl">
        <h2 id="explore-more-title">{t('eventsShowcase.title')}</h2>
        <p className="mt-3 text-base leading-7">{t('eventsShowcase.description')}</p>
        <div className="landing-explore-grid">
          <article className="explore-feature explore-feature-recap">
            <div className="explore-feature-copy">
              <p className="explore-feature-eyebrow">
                <Images size={16} aria-hidden="true" />
                {t('recaps.eyebrow')}
              </p>
              <h3>{t('eventsShowcase.recap.title')}</h3>
              <p className="explore-feature-description">{t('eventsShowcase.recap.description')}</p>
              <Link to="/events/recap" className="explore-feature-link">
                {t('eventsShowcase.recap.action')}
                <ArrowUpRight size={18} aria-hidden="true" />
              </Link>
            </div>
            <div className="explore-feature-visual explore-recap-visual">
              {latest && photo ? (
                <RecapImage
                  key={`${latest.id}/${photo.id}`}
                  recapId={latest.id}
                  photo={photo}
                  fallback={<MemoryArtwork />}
                />
              ) : (
                <MemoryArtwork />
              )}
            </div>
          </article>
          <article className="explore-feature explore-feature-merchandise">
            <div className="explore-feature-copy">
              <p className="explore-feature-eyebrow">
                <span className="explore-coming-soon">{t('features.merchPending')}</span>
              </p>
              <h3>{t('eventsShowcase.merchandise.title')}</h3>
              <p className="explore-feature-description">
                {t('eventsShowcase.merchandise.description')}
              </p>
              <Link to="/merchandise" className="explore-feature-link">
                {t('eventsShowcase.merchandise.action')}
                <ArrowUpRight size={18} aria-hidden="true" />
              </Link>
            </div>
            <div className="explore-feature-visual explore-merchandise-visual">
              <MerchandiseArtwork />
            </div>
          </article>
        </div>
      </div>
    </div>
  )
}
export { EventsExploreMore }
