import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { useTranslation } from 'react-i18next'

import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { ConfirmDialog } from '@/components/ui/confirm-dialog'
import { Typography } from '@/components/ui/typography'
import {
  categories,
  evidenceTypes,
  knowledgeClient,
  type BuiltinFaq,
  type Faq,
  type FaqCommand,
  type FaqContent,
} from '@/features/admin-knowledge'
import { normalizeApiError } from '@/lib/api'

export const knowledgeInput =
  'min-h-11 w-full min-w-0 rounded-md border border-input bg-background px-3 py-2 text-sm text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring'

function emptyDraft(builtin: BuiltinFaq | null): FaqContent {
  return {
    category: builtin?.category ?? 'faq',
    en: { questions: builtin ? [builtin.en] : [], answer: '' },
    de: { questions: builtin ? [builtin.de] : [], answer: '' },
    source_title: '',
    source_url: '',
    evidence: 'unsupported',
  }
}

export function KnowledgeEditor({
  initial,
  builtin,
  userId,
  onClose,
}: {
  initial: Faq | null
  builtin: BuiltinFaq | null
  userId: string | undefined
  onClose: () => void
}) {
  const { t, i18n } = useTranslation()
  const cache = useQueryClient()
  const key = ['private', userId, 'knowledge-base'] as const
  const [saved, setSaved] = useState(initial)
  const [content, setContent] = useState(() => initial?.content ?? emptyDraft(builtin))
  const [question, setQuestion] = useState('')
  const [confirmation, setConfirmation] = useState<Exclude<FaqCommand, { action: 'save' }> | null>(
    null,
  )
  const [historyOpen, setHistoryOpen] = useState(false)
  const [historyPage, setHistoryPage] = useState(1)
  const [notice, setNotice] = useState('')
  const builtinId = saved?.builtin_id ?? builtin?.id ?? null
  const dirty = !saved || JSON.stringify(content) !== JSON.stringify(saved.content)

  const history = useQuery({
    queryKey: [...key, 'history', saved?.id, historyPage],
    queryFn: ({ signal }) => knowledgeClient.history(saved!.id, historyPage, signal),
    enabled: Boolean(saved && historyOpen),
    meta: { private: true },
  })
  const change = useMutation({
    gcTime: 0,
    mutationFn: (command: FaqCommand) =>
      command.action === 'save'
        ? knowledgeClient.save(saved, content, builtinId)
        : knowledgeClient.change(saved!, command),
    onSuccess: (next) => {
      setSaved(next)
      setContent(next.content)
      setConfirmation(null)
      setHistoryPage(1)
      setNotice('kb.saved')
      void cache.invalidateQueries({ queryKey: key })
    },
  })
  const preview = useMutation({
    gcTime: 0,
    mutationFn: () => knowledgeClient.preview(question, content, saved?.id ?? null, builtinId),
  })
  const reload = useMutation({
    gcTime: 0,
    mutationFn: () => knowledgeClient.detail(saved!.id),
    onSuccess: (latest) => {
      // Only this explicit action replaces the form with the latest server draft.
      setSaved(latest)
      setContent(latest.content)
      setConfirmation(null)
      change.reset()
      preview.reset()
      setNotice('kb.reloaded')
    },
  })
  const busy = change.isPending || preview.isPending || reload.isPending
  const errorText = (error: unknown) => {
    const result = normalizeApiError(error)
    return t(result.reason ? 'kb.errors.' + result.reason : 'kb.errors.' + result.code, {
      defaultValue: t('kb.error'),
    })
  }
  const patch = (update: Partial<FaqContent>) => {
    setContent((previous) => ({ ...previous, ...update }))
    preview.reset()
    setNotice('')
  }
  const setLocale = (lang: 'en' | 'de', update: Partial<FaqContent['en']>) =>
    patch({ [lang]: { ...content[lang], ...update } })
  const operation =
    confirmation?.action === 'restore'
      ? confirmation.publish
        ? 'restorePublic'
        : 'restoreDraft'
      : (confirmation?.action ?? 'publish')
  const dialogLabel = t('kb.' + operation)
  const error = change.error ?? reload.error
  const conflict = normalizeApiError(error).reason === 'stale_version'

  return (
    <Card className="min-w-0 space-y-5 p-4 sm:p-6">
      <header className="flex flex-wrap items-center justify-between gap-2">
        <Typography as="h2" variant="h4">
          {t(saved ? 'kb.edit' : 'kb.new')}
        </Typography>
        <Button variant="ghost" className="min-h-11" disabled={busy} onClick={onClose}>
          {t('kb.close')}
        </Button>
      </header>
      {builtinId && <p className="break-words text-sm">{t('kb.replacing', { id: builtinId })}</p>}
      {saved && (
        <p className="text-sm text-muted-foreground">
          {t('kb.statuses.' + saved.status)} · {t('kb.revision', { number: saved.draft_revision })}
          {saved.published_revision !== null &&
            ' · ' + t('kb.publishedRevision', { number: saved.published_revision })}
        </p>
      )}
      <form
        onSubmit={(event) => {
          event.preventDefault()
          if (!busy) change.mutate({ action: 'save' })
        }}
      >
        <fieldset disabled={busy} className="min-w-0 space-y-4">
          <div className="grid gap-3 sm:grid-cols-2">
            <label className="min-w-0 space-y-1 text-sm">
              {t('kb.category')}
              <select
                className={knowledgeInput}
                value={content.category}
                onChange={(e) => patch({ category: e.target.value as FaqContent['category'] })}
              >
                {categories.map((item) => (
                  <option key={item} value={item}>
                    {t('kb.categories.' + item)}
                  </option>
                ))}
              </select>
            </label>
            <label className="min-w-0 space-y-1 text-sm">
              {t('kb.evidence')}
              <select
                className={knowledgeInput}
                value={content.evidence}
                onChange={(e) => patch({ evidence: e.target.value as FaqContent['evidence'] })}
              >
                {evidenceTypes.map((item) => (
                  <option key={item} value={item}>
                    {t('kb.evidenceTypes.' + item)}
                  </option>
                ))}
              </select>
            </label>
          </div>
          <p className="text-sm text-muted-foreground">{t('kb.policy')}</p>
          <div className="grid gap-4 lg:grid-cols-2">
            {(['en', 'de'] as const).map((lang) => (
              <fieldset
                key={lang}
                className="min-w-0 space-y-3 rounded-md border border-border p-3"
              >
                <legend className="px-1 text-sm font-semibold">{t('kb.languages.' + lang)}</legend>
                <label className="block space-y-1 text-sm">
                  {t('kb.question')}
                  <input
                    className={knowledgeInput}
                    maxLength={500}
                    value={content[lang].questions[0] ?? ''}
                    onChange={(e) =>
                      setLocale(lang, {
                        questions: [e.target.value, ...content[lang].questions.slice(1)],
                      })
                    }
                  />
                </label>
                <label className="block space-y-1 text-sm">
                  {t('kb.aliases')}
                  <textarea
                    className={knowledgeInput}
                    rows={2}
                    maxLength={7014}
                    value={content[lang].questions.slice(1).join('\n')}
                    onChange={(e) =>
                      setLocale(lang, {
                        questions: [
                          content[lang].questions[0] ?? '',
                          ...(e.target.value ? e.target.value.split('\n') : []),
                        ],
                      })
                    }
                  />
                </label>
                <label className="block space-y-1 text-sm">
                  {t('kb.answer')}
                  <textarea
                    className={knowledgeInput}
                    rows={5}
                    maxLength={1800}
                    value={content[lang].answer}
                    onChange={(e) => setLocale(lang, { answer: e.target.value })}
                  />
                </label>
              </fieldset>
            ))}
          </div>
          <div className="grid gap-3 sm:grid-cols-2">
            <label className="min-w-0 space-y-1 text-sm">
              {t('kb.sourceTitle')}
              <input
                className={knowledgeInput}
                maxLength={160}
                value={content.source_title}
                onChange={(e) => patch({ source_title: e.target.value })}
              />
            </label>
            <label className="min-w-0 space-y-1 text-sm">
              {t('kb.sourceUrl')}
              <input
                className={knowledgeInput}
                type="url"
                maxLength={300}
                value={content.source_url}
                onChange={(e) => patch({ source_url: e.target.value })}
              />
            </label>
          </div>
          <div className="flex flex-wrap gap-2">
            <Button type="submit" className="min-h-11">
              {t('kb.save')}
            </Button>
            {saved && saved.published_revision !== saved.draft_revision && (
              <Button
                type="button"
                variant="outline"
                className="min-h-11"
                disabled={dirty}
                onClick={() => {
                  change.reset()
                  setConfirmation({ action: 'publish' })
                }}
              >
                {t('kb.publish')}
              </Button>
            )}
            {saved?.published_revision != null && (
              <Button
                type="button"
                variant="outline"
                className="min-h-11"
                disabled={dirty}
                onClick={() => {
                  change.reset()
                  setConfirmation({ action: 'unpublish' })
                }}
              >
                {t('kb.unpublish')}
              </Button>
            )}
          </div>
        </fieldset>
      </form>
      {notice && <p role="status">{t(notice)}</p>}
      {error && (
        <div role="alert" className="space-y-2 text-sm">
          <p>{errorText(error)}</p>
          {saved && conflict && (
            <Button
              variant="outline"
              className="h-auto min-h-11 max-w-full whitespace-normal py-2"
              disabled={busy}
              onClick={() => reload.mutate()}
            >
              {t('kb.reload')}
            </Button>
          )}
        </div>
      )}

      <form
        className="space-y-2 border-t border-border pt-4"
        onSubmit={(event) => {
          event.preventDefault()
          if (!busy && question.trim()) preview.mutate()
        }}
      >
        <Typography as="h3" variant="h4">
          {t('kb.preview')}
        </Typography>
        <label className="block space-y-1 text-sm">
          {t('kb.testQuestion')}
          <input
            className={knowledgeInput}
            maxLength={500}
            value={question}
            disabled={busy}
            onChange={(e) => {
              setQuestion(e.target.value)
              preview.reset()
            }}
          />
        </label>
        <Button
          type="submit"
          variant="outline"
          className="min-h-11"
          disabled={busy || !question.trim()}
        >
          {t('kb.preview')}
        </Button>
      </form>
      {preview.isPending && <p role="status">{t('kb.loading')}</p>}
      {preview.isError && <p role="alert">{errorText(preview.error)}</p>}
      {preview.data && (
        <Card aria-live="polite" className="min-w-0 space-y-2 break-words p-4">
          <p className="font-semibold">
            {t('kb.selected.' + preview.data.selected)} ·{' '}
            {preview.data.answer.language.toUpperCase()}
          </p>
          <p>{preview.data.question}</p>
          <p className="whitespace-pre-wrap">{preview.data.answer.answer}</p>
          {preview.data.issue && (
            <p>{t('kb.errors.' + preview.data.issue, { defaultValue: t('kb.error') })}</p>
          )}
          {preview.data.answer.sources.map((source) => (
            <p key={source.entry_id} className="text-sm">
              {source.entry_id} · {t('kb.citations.' + source.verification_status)}
            </p>
          ))}
        </Card>
      )}

      {saved && (
        <section className="space-y-3 border-t border-border pt-4">
          <Button
            variant="outline"
            aria-expanded={historyOpen}
            onClick={() => setHistoryOpen(!historyOpen)}
          >
            {t('kb.history')}
          </Button>
          {historyOpen && history.isLoading && <p role="status">{t('kb.loading')}</p>}
          {historyOpen && history.isError && (
            <Button variant="outline" onClick={() => void history.refetch()}>
              {t('kb.retry')}
            </Button>
          )}
          {historyOpen && history.data && (
            <>
              <ul className="space-y-2">
                {history.data.items.map((item) => (
                  <li
                    key={item.revision}
                    className="min-w-0 space-y-2 rounded-md border border-border p-3"
                  >
                    <details className="min-w-0 break-words">
                      <summary className="cursor-pointer">
                        {t('kb.revision', { number: item.revision })} ·{' '}
                        {new Date(item.created_at).toLocaleString(i18n.resolvedLanguage)}
                      </summary>
                      <p className="whitespace-pre-wrap">
                        {item.content.en.questions.join(' / ')} — {item.content.en.answer}
                      </p>
                      <p className="whitespace-pre-wrap">
                        {item.content.de.questions.join(' / ')} — {item.content.de.answer}
                      </p>
                      <p className="text-sm text-muted-foreground">
                        {t('kb.author', { id: item.author_id })}
                      </p>
                    </details>
                    <div className="flex flex-wrap gap-2">
                      {[false, true].map((publish) => (
                        <Button
                          key={String(publish)}
                          variant="outline"
                          className="h-auto min-h-11 max-w-full whitespace-normal py-2"
                          disabled={busy || dirty}
                          onClick={() => {
                            change.reset()
                            setConfirmation({ action: 'restore', revision: item.revision, publish })
                          }}
                        >
                          {t(publish ? 'kb.restorePublic' : 'kb.restoreDraft')}
                        </Button>
                      ))}
                    </div>
                  </li>
                ))}
              </ul>
              <div className="flex flex-wrap gap-2">
                <Button
                  variant="outline"
                  disabled={historyPage === 1 || history.isFetching}
                  onClick={() => setHistoryPage(historyPage - 1)}
                >
                  {t('kb.previous')}
                </Button>
                <Button
                  variant="outline"
                  disabled={!history.data.has_more || history.isFetching}
                  onClick={() => setHistoryPage(historyPage + 1)}
                >
                  {t('kb.next')}
                </Button>
              </div>
            </>
          )}
        </section>
      )}
      <ConfirmDialog
        open={confirmation !== null}
        onOpenChange={(open) => {
          if (!open) setConfirmation(null)
        }}
        title={dialogLabel}
        description={t('kb.confirm.' + operation)}
        confirmLabel={t('kb.confirmAction')}
        cancelLabel={t('kb.cancel')}
        isPending={change.isPending}
        error={change.error ? errorText(change.error) : undefined}
        onConfirm={() => {
          if (confirmation && !busy) change.mutate(confirmation)
        }}
      />
    </Card>
  )
}
