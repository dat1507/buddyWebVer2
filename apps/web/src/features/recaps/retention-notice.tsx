import { useTranslation } from 'react-i18next'
import { localized, type Recap } from './recaps'

export function RetentionNotice() {
  const { t } = useTranslation()
  return (
    <p className="rounded-xl border border-border bg-muted p-4 text-sm">
      {t('recaps.retentionWarning')}
    </p>
  )
}

export function EvictionNotice({
  items,
  pending,
}: {
  items: NonNullable<Recap['evicted_recaps']>
  pending: boolean
}) {
  const { t, i18n } = useTranslation()
  const de = i18n.resolvedLanguage?.startsWith('de') ?? false
  if (!items.length) return null
  return (
    <div role="status" className="rounded-xl border border-border bg-muted p-4">
      {items.map((item) => (
        <p key={item.id}>
          {t('recaps.evicted', { title: localized(item, 'title', de) || item.id })}
        </p>
      ))}
      {pending && <p>{t('recaps.cleanup')}</p>}
    </div>
  )
}
