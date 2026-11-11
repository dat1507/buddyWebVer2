import { useEffect, useRef } from 'react'
import { useTranslation } from 'react-i18next'

import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { type CatalogItem } from '@/features/admin-knowledge'

export function KnowledgeDetail({
  item,
  onClose,
  onEdit,
}: {
  item: CatalogItem
  onClose: () => void
  onEdit: () => void
}) {
  const { t } = useTranslation()
  const heading = useRef<HTMLHeadingElement>(null)
  useEffect(() => {
    heading.current?.focus()
  }, [])
  return (
    <Card className="min-w-0 space-y-4 break-words p-4 sm:p-6">
      <header className="flex flex-wrap items-center justify-between gap-2">
        <h2 ref={heading} tabIndex={-1} className="text-xl font-semibold">
          {t('kb.view')}
        </h2>
        <div className="flex flex-wrap gap-2">
          <Button variant="outline" className="min-h-11" onClick={onEdit}>
            {t('kb.edit')}
          </Button>
          <Button variant="ghost" className="min-h-11" onClick={onClose}>
            {t('kb.close')}
          </Button>
        </div>
      </header>
      <p>
        {t('kb.faqLabel')} · {t('kb.statuses.' + item.status)} ·{' '}
        {t('kb.categories.' + item.content.category)}
      </p>
      {item.managed && (
        <p className="text-sm">
          {t('kb.revision', { number: item.managed.draft_revision })}
          {item.managed.published_revision !== null &&
            ' · ' + t('kb.publishedRevision', { number: item.managed.published_revision })}
        </p>
      )}
      {item.builtin && item.managed?.published_revision == null && (
        <p className="text-sm text-muted-foreground">
          {t(
            item.builtin.status === 'verified_code' || item.builtin.status === 'verified_official'
              ? 'kb.builtinFallback'
              : 'kb.builtinExcluded',
          )}
        </p>
      )}
      {(['en', 'de'] as const).map((lang) => (
        <section
          key={lang}
          lang={lang}
          aria-label={t('kb.languages.' + lang)}
          className="min-w-0 space-y-2"
        >
          <h3 className="font-semibold">{t('kb.languages.' + lang)}</h3>
          <p className="font-semibold">{item.content[lang].questions[0] || t('kb.untitled')}</p>
          {item.content[lang].questions.length > 1 && (
            <div>
              <p className="text-sm text-muted-foreground">{t('kb.aliases')}</p>
              <ul className="list-inside list-disc">
                {item.content[lang].questions.slice(1).map((question, index) => (
                  <li key={index}>{question}</li>
                ))}
              </ul>
            </div>
          )}
          <p className="whitespace-pre-wrap">{item.content[lang].answer}</p>
        </section>
      ))}
      {item.builtin && item.managed?.published_revision == null && (
        <p className="text-sm text-muted-foreground">
          {t('kb.citations.' + item.builtin.status, { defaultValue: item.builtin.status })}
          {item.builtin.verified_on && ' · ' + item.builtin.verified_on}
        </p>
      )}
      {item.managed?.published_revision != null && (
        <p className="text-sm text-muted-foreground">
          {t('kb.evidenceTypes.' + item.content.evidence)}
        </p>
      )}
      {item.sources.length > 0 && (
        <section className="space-y-2">
          <h3 className="font-semibold">{t('kb.references')}</h3>
          {item.sources.map((source) => (
            <p key={source.reference} className="text-sm">
              {source.title} · <span className="[overflow-wrap:anywhere]">{source.reference}</span>
            </p>
          ))}
        </section>
      )}
      {item.managed && <p className="text-sm text-muted-foreground">{t('kb.draftAccess')}</p>}
    </Card>
  )
}
