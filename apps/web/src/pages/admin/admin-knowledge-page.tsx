import { useQuery } from '@tanstack/react-query'
import { BookOpen, Plus } from 'lucide-react'
import { useState } from 'react'
import { useTranslation } from 'react-i18next'

import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { Typography } from '@/components/ui/typography'
import {
  categories,
  knowledgeClient,
  statuses,
  type BuiltinFaq,
  type Faq,
} from '@/features/admin-knowledge'
import { KnowledgeEditor, knowledgeInput } from '@/features/admin-knowledge-editor'
import { useAuthStore } from '@/stores/auth-store'

export function AdminKnowledgePage() {
  const { t, i18n } = useTranslation()
  const userId = useAuthStore((state) => state.user?.id)
  const [view, setView] = useState<'faqs' | 'references'>('faqs')
  const [search, setSearch] = useState('')
  const [filter, setFilter] = useState('')
  const [category, setCategory] = useState('')
  const [status, setStatus] = useState('')
  const [page, setPage] = useState(1)
  const [editor, setEditor] = useState<{ faq: Faq | null; builtin: BuiltinFaq | null } | null>(null)
  const params = new URLSearchParams({ search: filter, page: String(page) })
  if (category) params.set('category', category)
  if (status) params.set('status', status)

  const results = useQuery({
    queryKey: ['private', userId, 'knowledge-base', 'list', params.toString()],
    queryFn: ({ signal }) => knowledgeClient.list(params, signal),
    enabled: Boolean(userId) && view === 'faqs',
    meta: { private: true },
  })
  const references = useQuery({
    queryKey: ['private', userId, 'knowledge-base', 'references'],
    queryFn: ({ signal }) => knowledgeClient.references(signal),
    enabled: Boolean(userId) && view === 'references',
    meta: { private: true },
  })
  const query = view === 'faqs' ? results : references
  const lang = i18n.resolvedLanguage === 'de' ? 'de' : 'en'

  return (
    <section className="min-w-0 space-y-4 py-6">
      <header>
        <Typography as="h1" variant="h3">
          {t('kb.title')}
        </Typography>
        <Typography variant="muted">{t('kb.description')}</Typography>
      </header>
      {editor ? (
        <KnowledgeEditor
          initial={editor.faq}
          builtin={editor.builtin}
          userId={userId}
          onClose={() => setEditor(null)}
        />
      ) : (
        <>
          <div className="flex flex-wrap gap-2" role="group" aria-label={t('kb.sections')}>
            <Button
              variant={view === 'faqs' ? 'default' : 'outline'}
              aria-pressed={view === 'faqs'}
              onClick={() => setView('faqs')}
            >
              {t('kb.faqs')}
            </Button>
            <Button
              variant={view === 'references' ? 'default' : 'outline'}
              aria-pressed={view === 'references'}
              onClick={() => setView('references')}
            >
              <BookOpen aria-hidden="true" />
              {t('kb.references')}
            </Button>
          </div>
          {view === 'faqs' && (
            <Card className="min-w-0 space-y-3 p-4">
              <form
                className="flex flex-wrap items-end gap-2"
                onSubmit={(event) => {
                  event.preventDefault()
                  setFilter(search.trim())
                  setPage(1)
                }}
              >
                <label className="min-w-0 flex-1 space-y-1 text-sm">
                  {t('kb.search')}
                  <input
                    className={knowledgeInput}
                    type="search"
                    maxLength={100}
                    value={search}
                    onChange={(event) => setSearch(event.target.value)}
                  />
                </label>
                <Button type="submit" variant="outline" className="min-h-11">
                  {t('kb.search')}
                </Button>
              </form>
              <div className="grid gap-2 sm:grid-cols-2">
                <label className="min-w-0 space-y-1 text-sm">
                  {t('kb.category')}
                  <select
                    className={knowledgeInput}
                    value={category}
                    onChange={(e) => {
                      setCategory(e.target.value)
                      setPage(1)
                    }}
                  >
                    <option value="">{t('kb.allCategories')}</option>
                    {categories.map((item) => (
                      <option key={item} value={item}>
                        {t('kb.categories.' + item)}
                      </option>
                    ))}
                  </select>
                </label>
                <label className="min-w-0 space-y-1 text-sm">
                  {t('kb.publication')}
                  <select
                    className={knowledgeInput}
                    value={status}
                    onChange={(e) => {
                      setStatus(e.target.value)
                      setPage(1)
                    }}
                  >
                    <option value="">{t('kb.allStatuses')}</option>
                    {statuses.map((item) => (
                      <option key={item} value={item}>
                        {t('kb.statuses.' + item)}
                      </option>
                    ))}
                  </select>
                </label>
              </div>
              <Button className="min-h-11" onClick={() => setEditor({ faq: null, builtin: null })}>
                <Plus aria-hidden="true" />
                {t('kb.new')}
              </Button>
            </Card>
          )}
          {query.isLoading && <p role="status">{t('kb.loading')}</p>}
          {query.isError && (
            <div role="alert" className="space-y-2">
              <p>{t('kb.error')}</p>
              <Button variant="outline" onClick={() => void query.refetch()}>
                {t('kb.retry')}
              </Button>
            </div>
          )}
          {view === 'faqs' && results.data && (
            <>
              {!results.data.items.length && <p>{t('kb.empty')}</p>}
              <ul className="space-y-2">
                {results.data.items.map((item) => (
                  <li key={item.id}>
                    <Card className="flex min-w-0 flex-wrap items-center justify-between gap-2 p-4">
                      <div className="min-w-0 break-words">
                        <p className="font-semibold">
                          {item.content[lang].questions[0] || t('kb.untitled')}
                        </p>
                        <p className="text-sm text-muted-foreground">
                          {t('kb.managed')} · {t('kb.statuses.' + item.status)} ·{' '}
                          {t('kb.categories.' + item.content.category)}
                        </p>
                      </div>
                      <Button
                        variant="outline"
                        className="min-h-11"
                        onClick={() => setEditor({ faq: item, builtin: null })}
                      >
                        {t('kb.edit')}
                      </Button>
                    </Card>
                  </li>
                ))}
              </ul>
              <div className="flex flex-wrap items-center gap-2">
                <Button
                  variant="outline"
                  disabled={page === 1 || results.isFetching}
                  onClick={() => setPage(page - 1)}
                >
                  {t('kb.previous')}
                </Button>
                <span>{t('kb.page', { number: page })}</span>
                <Button
                  variant="outline"
                  disabled={!results.data.has_more || results.isFetching}
                  onClick={() => setPage(page + 1)}
                >
                  {t('kb.next')}
                </Button>
              </div>
            </>
          )}
          {view === 'references' && references.data && (
            <>
              <Card className="space-y-2 p-4">
                <Typography as="h2" variant="h4">
                  {t('kb.guide')}
                </Typography>
                <p className="text-sm">
                  {references.data.owner_guide} · {t('kb.guideDescription')}
                </p>
              </Card>
              <ul className="space-y-2">
                {references.data.builtin.map((item) => (
                  <li key={item.id}>
                    <Card className="flex min-w-0 flex-wrap items-center justify-between gap-2 p-4">
                      <div className="min-w-0 break-words">
                        <p className="font-semibold">{item[lang]}</p>
                        <p className="text-sm text-muted-foreground">
                          {t('kb.builtin')} · {t('kb.citations.' + item.status)}
                        </p>
                      </div>
                      <Button
                        variant="outline"
                        className="min-h-11"
                        onClick={() => setEditor({ faq: null, builtin: item })}
                      >
                        {t('kb.replace')}
                      </Button>
                    </Card>
                  </li>
                ))}
              </ul>
            </>
          )}
        </>
      )}
    </section>
  )
}
