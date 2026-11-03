import { useEffect, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import { ArrowLeft, ArrowRight, X } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { Link } from 'react-router'
import { useModalIsolation } from '@/hooks/use-modal-isolation'
import { localized, type Recap } from './recaps'
import { RecapImage } from './recap-photo'

function Lightbox({
  recap,
  start,
  admin,
  close,
}: {
  recap: Recap
  start: number
  admin: boolean
  close: () => void
}) {
  const { t, i18n } = useTranslation()
  const [index, setIndex] = useState(start)
  const ref = useRef<HTMLDivElement>(null)
  const closeRef = useRef<HTMLButtonElement>(null)
  const onClose = useRef(close)
  useModalIsolation(ref)
  useEffect(() => {
    onClose.current = close
  }, [close])
  useEffect(() => {
    const previous = document.activeElement as HTMLElement | null
    const overflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    closeRef.current?.focus()
    const keydown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') onClose.current()
      if (event.key === 'ArrowRight') setIndex((value) => (value + 1) % recap.photos.length)
      if (event.key === 'ArrowLeft')
        setIndex((value) => (value + recap.photos.length - 1) % recap.photos.length)
      if (event.key === 'Tab') {
        const buttons = ref.current?.querySelectorAll<HTMLButtonElement>('button:not(:disabled)')
        if (!buttons?.length) return
        const first = buttons[0]
        const last = buttons[buttons.length - 1]
        if (event.shiftKey && document.activeElement === first) {
          event.preventDefault()
          last.focus()
        } else if (!event.shiftKey && document.activeElement === last) {
          event.preventDefault()
          first.focus()
        }
      }
    }
    document.addEventListener('keydown', keydown)
    return () => {
      document.removeEventListener('keydown', keydown)
      document.body.style.overflow = overflow
      previous?.focus()
    }
  }, [recap.photos.length])
  const photo = recap.photos[index]
  return createPortal(
    <div
      ref={ref}
      className="recap-lightbox"
      role="dialog"
      aria-modal="true"
      aria-label={t('recaps.gallery')}
    >
      <button
        ref={closeRef}
        onClick={close}
        aria-label={t('recaps.close')}
        className="recap-lightbox-close"
      >
        <X aria-hidden="true" />
      </button>
      <figure>
        <RecapImage key={photo.id} recapId={recap.id} photo={photo} display admin={admin} />
        <figcaption>
          {localized(photo, 'caption', i18n.resolvedLanguage?.startsWith('de') ?? false)}
        </figcaption>
      </figure>
      <div className="recap-lightbox-controls">
        <button
          onClick={() => setIndex((index + recap.photos.length - 1) % recap.photos.length)}
          aria-label={t('recaps.previous')}
          disabled={recap.photos.length < 2}
        >
          <ArrowLeft aria-hidden="true" />
        </button>
        <span role="status" aria-live="polite">
          {index + 1} / {recap.photos.length}
        </span>
        <button
          onClick={() => setIndex((index + 1) % recap.photos.length)}
          aria-label={t('recaps.next')}
          disabled={recap.photos.length < 2}
        >
          <ArrowRight aria-hidden="true" />
        </button>
      </div>
    </div>,
    document.body,
  )
}

export function RecapStory({ recap, admin = false }: { recap: Recap; admin?: boolean }) {
  const { t, i18n } = useTranslation()
  const [opened, setOpened] = useState<number | null>(null)
  const de = i18n.resolvedLanguage?.startsWith('de') ?? false
  const photoButton = (index: number) => {
    const photo = recap.photos[index]
    return (
      <figure key={photo.id}>
        <button
          type="button"
          className="recap-photo-button"
          onClick={() => setOpened(index)}
          aria-label={`${t('recaps.openPhoto')} ${index + 1}: ${localized(photo, 'alt', de)}`}
        >
          <RecapImage recapId={recap.id} photo={photo} admin={admin} />
        </button>
        {localized(photo, 'caption', de) && (
          <figcaption>{localized(photo, 'caption', de)}</figcaption>
        )}
      </figure>
    )
  }
  return (
    <article className="recap-shell recap-detail">
      <Link className="recap-back" to={admin ? '/admin/events/recaps' : '/events/recap'}>
        <ArrowLeft aria-hidden="true" size={18} />
        {t('recaps.backAll')}
      </Link>
      {admin && <p className="recap-eyebrow">{t('recaps.previewNotice')}</p>}
      <header className="recap-detail-header">
        <p className="recap-eyebrow">{t('recaps.eyebrow')}</p>
        <h1>{localized(recap, 'title', de) || t('recaps.untitled')}</h1>
        {recap.event_date && (
          <time dateTime={recap.event_date}>
            {new Intl.DateTimeFormat(de ? 'de-DE' : 'en-GB', {
              dateStyle: 'long',
              timeZone: 'UTC',
            }).format(new Date(`${recap.event_date}T12:00:00Z`))}
          </time>
        )}
        <p>{localized(recap, 'summary', de)}</p>
      </header>
      {recap.photos.length > 0 && (
        <section aria-labelledby="recap-highlights">
          <h2 id="recap-highlights">{t('recaps.highlights')}</h2>
          <div className="recap-highlights" data-count={Math.min(5, recap.photos.length)}>
            {recap.photos.slice(0, 5).map((_, index) => photoButton(index))}
          </div>
        </section>
      )}
      {localized(recap, 'editorial', de) && (
        <p className="recap-editorial">{localized(recap, 'editorial', de)}</p>
      )}
      <section aria-labelledby="recap-gallery">
        <div className="recap-section-heading">
          <h2 id="recap-gallery">{t('recaps.gallery')}</h2>
          <span>{t('recaps.photoCount', { count: recap.photos.length })}</span>
        </div>
        <div className="recap-photo-grid">{recap.photos.map((_, index) => photoButton(index))}</div>
        {recap.photos.length === 0 && <p>{t('recaps.noPhotos')}</p>}
      </section>
      <footer className="recap-footer">
        <Link to={admin ? '/admin/events/recaps' : '/events/recap'}>{t('recaps.backAll')}</Link>
        <Link to="/#events">{t('recaps.backEvents')}</Link>
      </footer>
      {opened !== null && (
        <Lightbox recap={recap} start={opened} admin={admin} close={() => setOpened(null)} />
      )}
    </article>
  )
}
