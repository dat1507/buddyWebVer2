import { useQuery } from '@tanstack/react-query'
import { ArrowLeft, ArrowUpRight } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { Link, useParams, useSearchParams } from 'react-router'
import { ApiError } from '@/lib/api'
import { fetchRecap, fetchRecaps, isUuid, localized } from '@/features/recaps/recaps'
import { RecapImage } from '@/features/recaps/recap-photo'
import { RecapStory } from '@/features/recaps/recap-story'
import '@/features/recaps/recaps.css'

export function RecapGalleryPage() {
  const { t, i18n } = useTranslation()
  const [params, setParams] = useSearchParams()
  const rawPage = Number(params.get('page') ?? 1)
  const page = Number.isSafeInteger(rawPage) && rawPage > 0 ? rawPage : 1
  const year = /^\d{4}$/.test(params.get('year') ?? '') ? params.get('year')! : ''
  const de = i18n.resolvedLanguage?.startsWith('de') ?? false
  const query = useQuery({
    queryKey: ['recaps', page, year],
    queryFn: ({ signal }) => fetchRecaps(page, year, false, signal),
    staleTime: 30_000,
  })
  return (
    <main className="community-surface recap-page">
      <div className="recap-shell">
        <Link to="/#events" className="recap-back">
          <ArrowLeft size={18} aria-hidden="true" />
          {t('recaps.backEvents')}
        </Link>
        <header className="recap-hero">
          <div>
            <p className="recap-eyebrow">{t('recaps.eyebrow')}</p>
            <h1>{t('recaps.hero')}</h1>
            <p>{t('recaps.intro')}</p>
            <a href="#memories" className="recap-pill">
              {t('recaps.explore')} <ArrowUpRight size={18} aria-hidden="true" />
            </a>
          </div>
          {!!query.data?.mosaic.length && (
            <div className="recap-mosaic" data-count={query.data.mosaic.length}>
              {query.data.mosaic.map((recap) => {
                const photo =
                  recap.photos.find((item) => item.id === recap.thumbnail_id) ?? recap.photos[0]
                return photo ? (
                  <Link
                    key={recap.id}
                    to={`/events/recap/${recap.id}`}
                    aria-label={localized(recap, 'title', de)}
                  >
                    <RecapImage recapId={recap.id} photo={photo} />
                  </Link>
                ) : null
              })}
            </div>
          )}
        </header>
        <section id="memories" aria-labelledby="memories-heading">
          <div className="recap-section-heading">
            <div>
              <p className="recap-eyebrow">{t('recaps.collection')}</p>
              <h2 id="memories-heading">{t('recaps.explore')}</h2>
            </div>
            <label className="recap-filter">
              {t('recaps.year')}
              <select
                value={year}
                onChange={(event) =>
                  setParams(event.target.value ? { year: event.target.value } : {})
                }
              >
                <option value="">{t('recaps.all')}</option>
                {query.data?.years.map((value) => (
                  <option key={value}>{value}</option>
                ))}
              </select>
            </label>
          </div>
          {query.isPending && <p role="status">{t('recaps.loading')}</p>}
          {query.isError && (
            <div role="alert">
              <p>{t('recaps.error')}</p>
              <button className="recap-pill" onClick={() => void query.refetch()}>
                {t('recaps.retry')}
              </button>
            </div>
          )}
          {query.data && query.data.items.length === 0 && (
            <div className="recap-empty">
              <h3>{t('recaps.empty')}</h3>
              <p>{t('recaps.emptyDescription')}</p>
            </div>
          )}
          <div className="recap-card-grid">
            {query.data?.items.map((recap) => {
              const photo =
                recap.photos.find((item) => item.id === recap.thumbnail_id) ?? recap.photos[0]
              return (
                <article key={recap.id} className="recap-card">
                  {photo && (
                    <Link tabIndex={-1} aria-hidden="true" to={`/events/recap/${recap.id}`}>
                      <RecapImage recapId={recap.id} photo={photo} />
                    </Link>
                  )}
                  <div className="recap-card-copy">
                    {recap.event_date && (
                      <time dateTime={recap.event_date}>
                        {new Intl.DateTimeFormat(de ? 'de-DE' : 'en-GB', {
                          dateStyle: 'medium',
                          timeZone: 'UTC',
                        }).format(new Date(`${recap.event_date}T12:00:00Z`))}
                      </time>
                    )}
                    <h3>{localized(recap, 'title', de)}</h3>
                    <p>{localized(recap, 'summary', de)}</p>
                    <Link to={`/events/recap/${recap.id}`}>
                      {t('recaps.view')}
                      <ArrowUpRight size={18} aria-hidden="true" />
                    </Link>
                  </div>
                </article>
              )
            })}
          </div>
          {query.data && query.data.total_pages > 1 && (
            <nav className="recap-pagination" aria-label={t('recaps.pagination')}>
              <button
                disabled={page <= 1}
                onClick={() => setParams({ ...(year ? { year } : {}), page: String(page - 1) })}
              >
                {t('recaps.previous')}
              </button>
              <span>
                {page} / {query.data.total_pages}
              </span>
              <button
                disabled={page >= query.data.total_pages}
                onClick={() => setParams({ ...(year ? { year } : {}), page: String(page + 1) })}
              >
                {t('recaps.next')}
              </button>
            </nav>
          )}
        </section>
      </div>
    </main>
  )
}

export function RecapDetailPage() {
  const { recapId } = useParams()
  const { t } = useTranslation()
  const query = useQuery({
    queryKey: ['recaps', recapId],
    queryFn: ({ signal }) => fetchRecap(recapId!, false, signal),
    enabled: isUuid(recapId),
    staleTime: 30_000,
    retry: 1,
  })
  return (
    <main className="community-surface recap-page">
      {!isUuid(recapId) || (query.error instanceof ApiError && query.error.status === 404) ? (
        <div className="recap-shell recap-empty">
          <h1>{t('recaps.notFound')}</h1>
          <Link to="/events/recap">{t('recaps.backAll')}</Link>
        </div>
      ) : query.data ? (
        <RecapStory recap={query.data} />
      ) : (
        <div className="recap-shell">
          <p role={query.isError ? 'alert' : 'status'}>
            {t(query.isError ? 'recaps.error' : 'recaps.loading')}
          </p>
          {query.isError && (
            <button onClick={() => void query.refetch()}>{t('recaps.retry')}</button>
          )}
        </div>
      )}
    </main>
  )
}
