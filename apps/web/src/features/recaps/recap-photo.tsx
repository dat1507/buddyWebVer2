import { useEffect, useRef, useState, type ReactNode } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useTranslation } from 'react-i18next'
import { localized, photoUrl, type RecapPhoto } from './recaps'

export function RecapImage({
  recapId,
  photo,
  display = false,
  admin = false,
  fallback,
}: {
  recapId: string
  photo: RecapPhoto
  display?: boolean
  admin?: boolean
  fallback?: ReactNode
}) {
  const { t, i18n } = useTranslation()
  const ref = useRef<HTMLSpanElement>(null)
  const [visible, setVisible] = useState(display || !window.IntersectionObserver)
  const [failedUrl, setFailedUrl] = useState<string | null>(null)
  const [retry, setRetry] = useState(0)
  useEffect(() => {
    if (visible || !ref.current) return
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setVisible(true)
          observer.disconnect()
        }
      },
      { rootMargin: '200px' },
    )
    observer.observe(ref.current)
    return () => observer.disconnect()
  }, [visible])
  const query = useQuery({
    queryKey: [admin ? 'private' : 'recap-media', recapId, photo.id, display, retry],
    queryFn: ({ signal }) => photoUrl(recapId, photo.id, display, admin, signal),
    enabled: visible,
    staleTime: 240_000,
    gcTime: 300_000,
    retry: 1,
    refetchInterval: visible ? 240_000 : false,
    meta: { private: admin },
  })
  const failed = query.isError || (query.data && failedUrl === query.data.url)
  return (
    <span ref={ref} className={`recap-image ${display ? 'recap-image-full' : ''}`}>
      {failed ? (
        display ? (
          <button
            type="button"
            onClick={() => {
              setRetry((value) => value + 1)
              setFailedUrl(null)
            }}
          >
            {t('recaps.retryImage')}
          </button>
        ) : fallback ? (
          <>
            {fallback}
            <span className="sr-only">{t('recaps.photoUnavailable')}</span>
          </>
        ) : (
          <span>{t('recaps.photoUnavailable')}</span>
        )
      ) : query.data ? (
        <img
          src={query.data.url}
          alt={localized(photo, 'alt', i18n.resolvedLanguage?.startsWith('de') ?? false)}
          width={photo.width}
          height={photo.height}
          loading={display ? 'eager' : 'lazy'}
          decoding="async"
          onError={() => {
            if (retry < 1) setRetry(1)
            else setFailedUrl(query.data!.url)
          }}
        />
      ) : (
        <>
          {fallback}
          <span
            role="status"
            className={fallback ? 'sr-only' : 'recap-image-loading'}
            aria-label={t('recaps.loading')}
          />
        </>
      )}
    </span>
  )
}
