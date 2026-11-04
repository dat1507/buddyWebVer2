import { useEffect, useRef, useState, type ChangeEvent } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { ArrowDown, ArrowUp, Plus, Trash2 } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { Link, useLocation, useNavigate, useParams, useSearchParams } from 'react-router'
import { Button } from '@/components/ui/button'
import { ConfirmDialog } from '@/components/ui/confirm-dialog'
import { RetentionNotice, EvictionNotice } from '@/features/recaps/retention-notice'
import { AdminEventsTabs } from '@/features/recaps/admin-events-tabs'
import { RecapImage } from '@/features/recaps/recap-photo'
import { RecapStory } from '@/features/recaps/recap-story'
import {
  fetchRecap,
  fetchRecaps,
  isUuid,
  localized,
  mutateRecap,
  relatedEventDate,
  recapSchema,
  type Recap,
} from '@/features/recaps/recaps'
import { adminEventsClient, type AdminEventList } from '@/features/admin-events/admin-events'
import { sessionClient } from '@/features/auth/session-client'
import { parseContract } from '@/features/matching/invitation'
import { ApiError } from '@/lib/api'
import '@/features/recaps/recaps.css'

const control =
  'w-full rounded-xl border border-input bg-background px-3 py-2.5 text-sm text-foreground focus-visible:outline focus-visible:outline-2 focus-visible:outline-ring'
const blank: Recap = {
  id: '',
  related_event_id: null,
  title_en: null,
  title_de: null,
  summary_en: null,
  summary_de: null,
  editorial_en: null,
  editorial_de: null,
  event_date: null,
  status: 'DRAFT',
  version: 1,
  thumbnail_id: null,
  photos: [],
  cleanup_pending: false,
}
const contentKeys = [
  'related_event_id',
  'title_en',
  'title_de',
  'summary_en',
  'summary_de',
  'editorial_en',
  'editorial_de',
  'event_date',
] as const
type Job = { id: string; file: File; state: 'queued' | 'uploading' | 'complete' | 'failed' }

export function AdminRecapsPage() {
  const { t, i18n } = useTranslation()
  const [params, setParams] = useSearchParams()
  const page = Math.max(1, Number(params.get('page')) || 1)
  const location = useLocation()
  const feedback = location.state as {
    evicted?: NonNullable<Recap['evicted_recaps']>
    pending?: boolean
  } | null
  const [cleanupError, setCleanupError] = useState(false)
  const query = useQuery({
    queryKey: ['private', 'recaps', page],
    queryFn: ({ signal }) => fetchRecaps(page, '', true, signal),
    meta: { private: true },
  })
  return (
    <section className="min-w-0 space-y-6 py-6">
      <AdminEventsTabs recap />
      <RetentionNotice />
      <EvictionNotice items={feedback?.evicted ?? []} pending={feedback?.pending ?? false} />
      <header className="flex flex-wrap items-center justify-between gap-4">
        <h1 className="text-3xl font-semibold">{t('recaps.recapTab')}</h1>
        <Button asChild>
          <Link to="/admin/events/recaps/new">
            <Plus aria-hidden="true" className="mr-2 size-4" />
            {t('recaps.new')}
          </Link>
        </Button>
      </header>
      {query.isPending && <p role="status">{t('recaps.loading')}</p>}
      {query.isError && (
        <div role="alert">
          <p>{t('recaps.error')}</p>
          <Button variant="outline" onClick={() => void query.refetch()}>
            {t('recaps.retry')}
          </Button>
        </div>
      )}
      {query.data?.items.length === 0 && <p>{t('recaps.emptyAdmin')}</p>}
      {cleanupError && <p role="alert">{t('recaps.mutationError')}</p>}
      {!!query.data?.pending_cleanup.length && (
        <div className="rounded-xl border border-border p-4">
          <p>{t('recaps.cleanup')}</p>
          {query.data.pending_cleanup.map((id) => (
            <Button
              key={id}
              variant="outline"
              onClick={async () => {
                try {
                  await sessionClient.authenticatedJson(`/admin/recaps/${id}/cleanup`, {
                    method: 'POST',
                  })
                  await query.refetch()
                } catch {
                  setCleanupError(true)
                }
              }}
            >
              {t('recaps.cleanupRetry')}
            </Button>
          ))}
        </div>
      )}
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        {query.data?.items.map((recap) => (
          <article key={recap.id} className="min-w-0 rounded-2xl border border-border bg-card p-5">
            <p className="text-xs font-semibold uppercase text-muted-foreground">
              {t(`recaps.${recap.status.toLowerCase()}`)}
            </p>
            <h2 className="my-3 break-words text-lg font-semibold">
              {localized(recap, 'title', i18n.resolvedLanguage?.startsWith('de') ?? false) ||
                t('recaps.untitled')}
            </h2>
            {recap.event_date && (
              <p className="mb-3 text-sm text-muted-foreground">{recap.event_date}</p>
            )}
            <Button asChild variant="outline">
              <Link to={`/admin/events/recaps/${recap.id}/edit`}>{t('recaps.edit')}</Link>
            </Button>
          </article>
        ))}
      </div>
      {query.data && query.data.total_pages > 1 && (
        <nav aria-label={t('recaps.pagination')} className="flex items-center gap-4">
          <Button
            variant="outline"
            disabled={page <= 1}
            onClick={() => setParams({ page: String(page - 1) })}
          >
            {t('recaps.previous')}
          </Button>
          <span>
            {page} / {query.data.total_pages}
          </span>
          <Button
            variant="outline"
            disabled={page >= query.data.total_pages}
            onClick={() => setParams({ page: String(page + 1) })}
          >
            {t('recaps.next')}
          </Button>
        </nav>
      )}
    </section>
  )
}

function FilePreview({ file }: { file: File }) {
  const imageRef = useRef<HTMLImageElement>(null)
  useEffect(() => {
    const value = URL.createObjectURL(file)
    if (imageRef.current) imageRef.current.src = value
    return () => URL.revokeObjectURL(value)
  }, [file])
  return <img ref={imageRef} alt="" className="size-16 rounded-lg object-cover" />
}

function RecapEditor({ initial }: { initial: Recap }) {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const cache = useQueryClient()
  const [draft, setDraft] = useState(initial)
  const saved = useRef(initial)
  const [snapshot, setSnapshot] = useState(initial)
  const [busy, setBusy] = useState(false)
  const lock = useRef(false)
  const [error, setError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)
  const [evicted, setEvicted] = useState<NonNullable<Recap['evicted_recaps']>>([])
  const [evictionPending, setEvictionPending] = useState(false)
  const [jobs, setJobs] = useState<Job[]>([])
  const [deletion, setDeletion] = useState<'recap' | string | null>(null)
  const [eventPage, setEventPage] = useState(1)
  const [eventSearch, setEventSearch] = useState('')
  const events = useQuery<AdminEventList>({
    queryKey: ['private', 'recap-events', eventPage, eventSearch],
    queryFn: () =>
      adminEventsClient.readEvents({
        page: eventPage,
        pageSize: 20,
        search: eventSearch,
        status: null,
        phase: null,
        from: null,
        to: null,
      }),
    meta: { private: true },
  })
  const dirty = JSON.stringify(draft) !== JSON.stringify(snapshot)
  useEffect(() => {
    const before = (event: BeforeUnloadEvent) => {
      if (dirty || lock.current) event.preventDefault()
    }
    window.addEventListener('beforeunload', before)
    return () => window.removeEventListener('beforeunload', before)
  }, [dirty])
  const accept = (value: Recap) => {
    saved.current = value
    setSnapshot(value)
    setDraft(value)
    cache.setQueryData(['private', 'recap', value.id], value)
  }
  const invalidate = async () => {
    await Promise.all([
      cache.invalidateQueries({ queryKey: ['private', 'recaps'] }),
      cache.invalidateQueries({ queryKey: ['recaps'] }),
    ])
  }
  const execute = async (action: () => Promise<void>) => {
    if (lock.current) return
    lock.current = true
    setBusy(true)
    setError(null)
    setNotice(null)
    setEvicted([])
    setEvictionPending(false)
    try {
      await action()
      await invalidate()
    } catch (reason) {
      setError(reason instanceof ApiError && reason.status === 409 ? 'conflict' : 'mutationError')
    } finally {
      lock.current = false
      setBusy(false)
    }
  }
  const content = () => Object.fromEntries(contentKeys.map((key) => [key, draft[key] || null]))
  const saveAll = async (): Promise<Recap> => {
    let result = await mutateRecap(draft.id ? `/${draft.id}` : '', draft.id ? 'PUT' : 'POST', {
      ...content(),
      ...(draft.id ? { version: saved.current.version } : {}),
    })
    saved.current = result
    if (draft.id && draft.photos.length) {
      result = await mutateRecap(`/${draft.id}/photos`, 'PUT', {
        version: result.version,
        thumbnail_id: draft.thumbnail_id,
        photos: draft.photos.map(({ id, alt_en, alt_de, caption_en, caption_de }) => ({
          id,
          alt_en,
          alt_de,
          caption_en,
          caption_de,
        })),
      })
    }
    accept(result)
    return result
  }
  const save = () =>
    void execute(async () => {
      const result = await saveAll()
      setNotice('saved')
      if (!draft.id) void navigate(`/admin/events/recaps/${result.id}/edit`, { replace: true })
    })
  const status = (value: Recap['status']) =>
    void execute(async () => {
      const result = await saveAll()
      const published = await mutateRecap(`/${result.id}/status`, 'PATCH', {
        version: result.version,
        status: value,
      })
      const removed = published.evicted_recaps ?? []
      if (removed.some((item) => item.id === result.id)) {
        void navigate('/admin/events/recaps', {
          state: { evicted: removed, pending: published.cleanup_pending },
        })
        return
      }
      accept(published)
      setEvicted(removed)
      setEvictionPending(published.cleanup_pending)
      setNotice(removed.length ? null : 'saved')
    })
  const runUploads = (selected: Job[]) =>
    void execute(async () => {
      let current = saved.current
      for (const job of selected) {
        setJobs((all) =>
          all.map((item) => (item.id === job.id ? { ...item, state: 'uploading' } : item)),
        )
        const data = new FormData()
        data.set('version', String(current.version))
        // Contextual initial alternatives can be refined independently for each photo below.
        data.set(
          'alt_en',
          `${current.title_en || 'Buddy community'} — ${job.file.name.replace(/\.[^.]+$/, '')}`.slice(
            0,
            200,
          ),
        )
        data.set(
          'alt_de',
          `${current.title_de || 'Buddy-Community'} — ${job.file.name.replace(/\.[^.]+$/, '')}`.slice(
            0,
            200,
          ),
        )
        data.set('file', job.file)
        try {
          current = parseContract(
            recapSchema,
            await sessionClient.authenticatedJson(
              `/admin/recaps/${current.id}/photos?upload_id=${job.id}`,
              { method: 'POST', formData: data },
            ),
          )
          accept(current)
          setJobs((all) =>
            all.map((item) => (item.id === job.id ? { ...item, state: 'complete' } : item)),
          )
        } catch {
          setJobs((all) =>
            all.map((item) => (item.id === job.id ? { ...item, state: 'failed' } : item)),
          )
          // A lost response may follow a committed upload. Fetch the version before the next file.
          try {
            current = await fetchRecap(current.id, true)
            accept(current)
          } catch {
            setError('mutationError')
            break
          }
        }
      }
      setNotice('uploadDone')
    })
  const addFiles = (files: FileList | null) => {
    if (!files || busy || dirty || !draft.id) return
    const selected = Array.from(files)
    if (
      draft.photos.length + selected.length > 12 ||
      selected.some(
        (file) =>
          file.size > 5 * 1024 * 1024 ||
          file.size === 0 ||
          !['image/jpeg', 'image/png', 'image/webp'].includes(file.type),
      )
    ) {
      setError('uploadInvalid')
      return
    }
    const batch = selected.map((file) => ({
      id: crypto.randomUUID(),
      file,
      state: 'queued' as const,
    }))
    setJobs((current) => [...current.filter((job) => job.state === 'failed'), ...batch])
    runUploads(batch)
  }
  const move = (index: number, delta: number) => {
    const photos = [...draft.photos]
    const [photo] = photos.splice(index, 1)
    photos.splice(index + delta, 0, photo)
    setDraft({ ...draft, photos: photos.map((item, sort_order) => ({ ...item, sort_order })) })
  }
  const remove = () =>
    void execute(async () => {
      const isRecap = deletion === 'recap'
      const path = `/admin/recaps/${draft.id}${isRecap ? '' : `/photos/${deletion}`}?version=${saved.current.version}`
      const payload = (await sessionClient.authenticatedJson(path, { method: 'DELETE' })) as {
        cleanup_pending: boolean
        thumbnail_changed: boolean
        recap: Recap | null
      }
      if (payload.cleanup_pending) setNotice('cleanup')
      else if (payload.thumbnail_changed) setNotice('thumbnailChanged')
      if (isRecap) {
        void navigate('/admin/events/recaps')
      } else if (payload.recap) accept(parseContract(recapSchema, payload.recap))
      setDeletion(null)
    })
  const field = (
    name: (typeof contentKeys)[number],
    label: string,
    multiline = false,
    limit = 120,
  ) => (
    <label key={name} className="block min-w-0 space-y-2 text-sm font-medium">
      {label}
      {multiline ? (
        <textarea
          className={control}
          rows={name.startsWith('editorial') ? 4 : 3}
          maxLength={limit}
          value={draft[name] ?? ''}
          onChange={(event) => setDraft({ ...draft, [name]: event.target.value })}
        />
      ) : (
        <input
          className={control}
          type={name === 'event_date' ? 'date' : 'text'}
          maxLength={limit}
          value={draft[name] ?? ''}
          onChange={(event) => setDraft({ ...draft, [name]: event.target.value || null })}
        />
      )}
    </label>
  )
  return (
    <div className="min-w-0 space-y-6">
      <header>
        <h1 className="text-3xl font-semibold">{t(draft.id ? 'recaps.edit' : 'recaps.new')}</h1>
        <p className="mt-2 text-sm font-semibold">
          {t('recaps.status')}: {t(`recaps.${draft.status.toLowerCase()}`)}
        </p>
        <p className="mt-2 text-sm text-muted-foreground">{t('recaps.requiredPublish')}</p>
      </header>
      <RetentionNotice />
      <EvictionNotice items={evicted} pending={evictionPending} />
      {error && (
        <div role="alert" className="rounded-xl border border-destructive p-4">
          <p>{t(`recaps.${error}`)}</p>
          {error === 'conflict' && (
            <Button
              variant="outline"
              disabled={busy}
              onClick={() =>
                void execute(async () => {
                  accept(await fetchRecap(draft.id, true))
                })
              }
            >
              {t('recaps.reload')}
            </Button>
          )}
        </div>
      )}
      {notice && (
        <p role="status" className="rounded-xl border border-border bg-muted p-4">
          {t(`recaps.${notice}`)}
        </p>
      )}
      {draft.cleanup_pending && !evicted.length && (
        <div role="status">
          <p>{t('recaps.cleanup')}</p>
          <Button
            variant="outline"
            disabled={busy}
            onClick={() =>
              void execute(async () => {
                await sessionClient.authenticatedJson(`/admin/recaps/${draft.id}/cleanup`, {
                  method: 'POST',
                })
                accept(await fetchRecap(draft.id, true))
              })
            }
          >
            {t('recaps.cleanupRetry')}
          </Button>
        </div>
      )}
      <fieldset
        disabled={busy}
        className="min-w-0 space-y-5 rounded-2xl border border-border bg-card p-5 sm:p-7"
      >
        <legend className="sr-only">{t('recaps.edit')}</legend>
        <div className="grid gap-5 sm:grid-cols-2">
          {field('title_en', `${t('recaps.title')} · EN`)}
          {field('title_de', `${t('recaps.title')} · DE`)}
          {field('summary_en', `${t('recaps.summary')} · EN`, true, 1000)}
          {field('summary_de', `${t('recaps.summary')} · DE`, true, 1000)}
          {field('event_date', t('recaps.eventDate'))}
          <div className="space-y-2">
            <label className="block text-sm font-medium" htmlFor="recap-event-search">
              {t('adminEvents.filters.search')}
            </label>
            <input
              id="recap-event-search"
              className={control}
              value={eventSearch}
              onChange={(event) => {
                setEventSearch(event.target.value)
                setEventPage(1)
              }}
              maxLength={100}
            />
            <label className="block text-sm font-medium" htmlFor="recap-related-event">
              {t('recaps.relatedEvent')}
            </label>
            <select
              id="recap-related-event"
              className={control}
              value={draft.related_event_id ?? ''}
              onChange={(event) => {
                const related = events.data?.items.find((item) => item.id === event.target.value)
                setDraft({
                  ...draft,
                  related_event_id: event.target.value || null,
                  ...(related && !draft.id
                    ? {
                        title_en: related.title_en,
                        title_de: related.title_de,
                        summary_en: related.description_en?.slice(0, 1000) ?? null,
                        summary_de: related.description_de?.slice(0, 1000) ?? null,
                        event_date: relatedEventDate(related.start_date, related.timezone),
                      }
                    : {}),
                })
              }}
            >
              <option value="">{t('recaps.standalone')}</option>
              {draft.related_event_id &&
                !events.data?.items.some((item) => item.id === draft.related_event_id) && (
                  <option value={draft.related_event_id}>{draft.related_event_id}</option>
                )}
              {events.data?.items.map((event) => (
                <option key={event.id} value={event.id}>
                  {event.title_en ?? event.title_de ?? t('recaps.untitled')}
                </option>
              ))}
            </select>
            {events.data && events.data.total_pages > 1 && (
              <div className="flex gap-2">
                <button
                  type="button"
                  disabled={eventPage === 1}
                  onClick={() => setEventPage(eventPage - 1)}
                >
                  {t('recaps.previous')}
                </button>
                <button
                  type="button"
                  disabled={eventPage >= events.data.total_pages}
                  onClick={() => setEventPage(eventPage + 1)}
                >
                  {t('recaps.next')}
                </button>
              </div>
            )}
          </div>
        </div>
        <details>
          <summary className="cursor-pointer py-3 text-sm font-semibold">
            {t('recaps.editorial')}
          </summary>
          <div className="grid gap-5 sm:grid-cols-2">
            {field('editorial_en', `${t('recaps.editorial')} · EN`, true, 10000)}
            {field('editorial_de', `${t('recaps.editorial')} · DE`, true, 10000)}
          </div>
        </details>
      </fieldset>
      <section className="space-y-4" aria-labelledby="recap-editor-photos">
        <h2 id="recap-editor-photos" className="text-xl font-semibold">
          {t('recaps.photos')} ({draft.photos.length}/12)
        </h2>
        <div
          className="rounded-2xl border-2 border-dashed border-border bg-card p-5"
          onDragOver={(event) => event.preventDefault()}
          onDrop={(event) => {
            event.preventDefault()
            addFiles(event.dataTransfer.files)
          }}
        >
          <label className="block space-y-3 font-medium">
            {t('recaps.upload')}
            <input
              type="file"
              accept="image/jpeg,image/png,image/webp"
              multiple
              disabled={busy || dirty || !draft.id || draft.photos.length >= 12}
              className="block max-w-full text-sm"
              onChange={(event: ChangeEvent<HTMLInputElement>) => {
                addFiles(event.target.files)
                event.target.value = ''
              }}
            />
          </label>
          <p className="mt-3 text-sm text-muted-foreground">{t('recaps.uploadHint')}</p>
        </div>
        <ul className="space-y-2" aria-live="polite">
          {jobs.map((job) => (
            <li
              key={job.id}
              className="flex min-w-0 flex-wrap items-center gap-3 rounded-xl border border-border p-3"
            >
              <FilePreview file={job.file} />
              <div className="min-w-0 flex-1">
                <p className="truncate text-sm">{job.file.name}</p>
                <p className="text-sm">{t(`recaps.${job.state}`)}</p>
                <progress
                  aria-label={`${job.file.name}: ${t(`recaps.${job.state}`)}`}
                  className="max-w-full"
                  max={100}
                  value={job.state === 'uploading' ? undefined : job.state === 'complete' ? 100 : 0}
                />
              </div>
              {job.state === 'failed' && (
                <Button
                  variant="outline"
                  disabled={busy || dirty}
                  onClick={() => runUploads([job])}
                >
                  {t('recaps.retry')}
                </Button>
              )}
            </li>
          ))}
        </ul>
        <ol className="space-y-4">
          {draft.photos.map((photo, index) => (
            <li
              key={photo.id}
              className="grid min-w-0 gap-5 rounded-2xl border border-border bg-card p-4 sm:grid-cols-[160px_minmax(0,1fr)]"
            >
              <div>
                <div className="aspect-[4/3] overflow-hidden rounded-xl">
                  <RecapImage recapId={draft.id} photo={photo} admin />
                </div>
                <div className="mt-3 flex flex-wrap gap-2">
                  <Button
                    variant="outline"
                    size="icon"
                    disabled={busy || index === 0}
                    aria-label={`${t('recaps.up')} ${index + 1}`}
                    onClick={() => move(index, -1)}
                  >
                    <ArrowUp aria-hidden="true" className="size-4" />
                  </Button>
                  <Button
                    variant="outline"
                    size="icon"
                    disabled={busy || index === draft.photos.length - 1}
                    aria-label={`${t('recaps.down')} ${index + 1}`}
                    onClick={() => move(index, 1)}
                  >
                    <ArrowDown aria-hidden="true" className="size-4" />
                  </Button>
                  <Button
                    variant="outline"
                    size="icon"
                    disabled={busy || dirty}
                    aria-label={`${t('recaps.remove')} ${index + 1}`}
                    onClick={() => setDeletion(photo.id)}
                  >
                    <Trash2 aria-hidden="true" className="size-4" />
                  </Button>
                </div>
                <button
                  type="button"
                  disabled={busy}
                  aria-pressed={(draft.thumbnail_id ?? draft.photos[0]?.id) === photo.id}
                  className="mt-3 min-h-11 text-left text-sm font-semibold text-primary"
                  onClick={() => setDraft({ ...draft, thumbnail_id: photo.id })}
                >
                  {t(
                    (draft.thumbnail_id ?? draft.photos[0]?.id) === photo.id
                      ? 'recaps.selectedThumbnail'
                      : 'recaps.thumbnail',
                  )}
                </button>
              </div>
              <div className="grid min-w-0 gap-4 sm:grid-cols-2">
                {(['alt_en', 'alt_de', 'caption_en', 'caption_de'] as const).map((name) => (
                  <label key={name} className="min-w-0 space-y-2 text-sm font-medium">
                    {t(name.startsWith('alt') ? 'recaps.alt' : 'recaps.caption')} ·{' '}
                    {name.endsWith('de') ? 'DE' : 'EN'} · {index + 1}
                    <textarea
                      className={control}
                      rows={2}
                      maxLength={name.startsWith('alt') ? 200 : 500}
                      disabled={busy}
                      value={photo[name] ?? ''}
                      onChange={(event) =>
                        setDraft({
                          ...draft,
                          photos: draft.photos.map((item) =>
                            item.id === photo.id ? { ...item, [name]: event.target.value } : item,
                          ),
                        })
                      }
                    />
                  </label>
                ))}
              </div>
            </li>
          ))}
        </ol>
      </section>
      <div className="flex flex-wrap gap-3 border-t border-border pt-5">
        <Button disabled={busy} onClick={save}>
          {t('recaps.save')}
        </Button>
        {draft.id && (
          <>
            <Button variant="outline" asChild disabled={busy || dirty}>
              <Link
                aria-disabled={busy || dirty}
                tabIndex={busy || dirty ? -1 : 0}
                onClick={(event) => {
                  if (busy || dirty) event.preventDefault()
                }}
                to={`/admin/events/recaps/${draft.id}/preview`}
              >
                {t('recaps.preview')}
              </Link>
            </Button>
            <Button
              disabled={busy}
              variant="outline"
              onClick={() => status(draft.status === 'PUBLISHED' ? 'DRAFT' : 'PUBLISHED')}
            >
              {t(draft.status === 'PUBLISHED' ? 'recaps.unpublish' : 'recaps.publish')}
            </Button>
            <Button
              variant="outline"
              disabled={busy || draft.status === 'ARCHIVED'}
              onClick={() => status('ARCHIVED')}
            >
              {t('recaps.archive')}
            </Button>
            <Button
              variant="destructive"
              disabled={busy || dirty}
              onClick={() => setDeletion('recap')}
            >
              {t('recaps.delete')}
            </Button>
          </>
        )}
        <Link
          className="inline-flex min-h-11 items-center px-4 text-sm underline"
          to="/admin/events/recaps"
        >
          {t('recaps.cancel')}
        </Link>
      </div>
      <ConfirmDialog
        open={deletion !== null}
        onOpenChange={(open) => {
          if (!open) setDeletion(null)
        }}
        onConfirm={remove}
        title={t(deletion === 'recap' ? 'recaps.deleteTitle' : 'recaps.removeConfirm')}
        description={t('recaps.deleteDescription')}
        confirmLabel={t('recaps.delete')}
        cancelLabel={t('recaps.cancel')}
        destructive
        isPending={busy}
      />
    </div>
  )
}

export function AdminRecapEditorPage({ preview = false }: { preview?: boolean }) {
  const { recapId } = useParams()
  const { t } = useTranslation()
  const query = useQuery({
    queryKey: ['private', 'recap', recapId],
    queryFn: ({ signal }) => fetchRecap(recapId!, true, signal),
    enabled: isUuid(recapId),
    meta: { private: true },
    refetchOnWindowFocus: false,
  })
  return (
    <section className="min-w-0 space-y-6 py-6">
      <AdminEventsTabs recap />
      {!recapId ? (
        <RecapEditor initial={blank} />
      ) : query.data ? (
        preview ? (
          <div className="community-surface recap-page rounded-2xl">
            <RecapStory recap={query.data} admin />
            <div className="recap-shell pb-6">
              <Link to={`/admin/events/recaps/${recapId}/edit`}>{t('recaps.edit')}</Link>
            </div>
          </div>
        ) : (
          <RecapEditor key={recapId} initial={query.data} />
        )
      ) : (
        <p role={query.isError ? 'alert' : 'status'}>
          {t(query.isError ? 'recaps.error' : 'recaps.loading')}
        </p>
      )}
    </section>
  )
}
