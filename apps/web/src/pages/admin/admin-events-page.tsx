import { useCallback, useEffect, useId, useMemo, useState } from 'react'
import { Plus, Search, X } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { Link } from 'react-router'

import { Button } from '@/components/ui/button'
import { DataTable, type DataTableColumn } from '@/components/ui/data-table'
import { Typography } from '@/components/ui/typography'
import {
  ADMIN_EVENTS_DEFAULT_PAGE_SIZE,
  type AdminEvent,
  type EventPhase,
  type EventStatus,
  type EventVisibility,
} from '@/features/admin-events/admin-events'
import { useAdminEvents } from '@/features/admin-events/queries/use-admin-events'
import { ApiError } from '@/lib/api'

const PAGE_SIZES = [10, 20, 50, 100] as const
const SEARCH_DEBOUNCE_MS = 300
const controlClassName =
  'h-10 min-w-0 rounded-md border border-input bg-background px-3 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring'

function utcBoundary(date: string, { end }: { end: boolean }): string | null {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(date)) return null
  const boundary = new Date(`${date}T00:00:00.000Z`)
  if (Number.isNaN(boundary.getTime())) return null
  if (end) boundary.setUTCDate(boundary.getUTCDate() + 1)
  return boundary.toISOString()
}

function EditorialBadge({ status }: { status: EventStatus }) {
  const { t } = useTranslation()
  const styles: Record<EventStatus, string> = {
    DRAFT: 'bg-muted text-muted-foreground',
    PUBLISHED: 'bg-emerald-500/10 text-emerald-700 dark:text-emerald-300',
    CANCELLED: 'bg-red-500/10 text-red-700 dark:text-red-300',
  }
  return (
    <span className={`inline-flex rounded-full px-2 py-1 text-xs font-semibold ${styles[status]}`}>
      {t(`adminEvents.status.${status}`)}
    </span>
  )
}

function AdminEventsPage() {
  const { t, i18n } = useTranslation()
  const titleId = useId()
  const searchId = useId()
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(ADMIN_EVENTS_DEFAULT_PAGE_SIZE)
  const [searchInput, setSearchInput] = useState('')
  const [search, setSearch] = useState('')
  const [status, setStatus] = useState<EventStatus | null>(null)
  const [visibility, setVisibility] = useState<EventVisibility | null>(null)
  const [phase, setPhase] = useState<EventPhase | null>(null)
  const [fromDate, setFromDate] = useState('')
  const [toDate, setToDate] = useState('')

  useEffect(() => {
    const timer = window.setTimeout(() => {
      setSearch(searchInput.trim())
      setPage(1)
    }, SEARCH_DEBOUNCE_MS)
    return () => window.clearTimeout(timer)
  }, [searchInput])

  const dateRangeComplete = Boolean(fromDate && toDate)
  const events = useAdminEvents({
    page,
    pageSize,
    search,
    status,
    visibility,
    phase,
    from: dateRangeComplete ? utcBoundary(fromDate, { end: false }) : null,
    to: dateRangeComplete ? utcBoundary(toDate, { end: true }) : null,
  })
  const lastPage = Math.max(1, events.data?.total_pages ?? 1)
  const isRecoveringPage = Boolean(events.data && page > lastPage)

  useEffect(() => {
    if (!events.data || page <= lastPage) return
    const timer = window.setTimeout(() => setPage((current) => Math.min(current, lastPage)), 0)
    return () => window.clearTimeout(timer)
  }, [events.data, lastPage, page])

  const language = i18n.resolvedLanguage?.startsWith('de') ? 'de-DE' : 'en-US'
  const unavailable = t('adminEvents.unavailable')
  const formatDate = useCallback(
    (value: string | null) =>
      value
        ? new Intl.DateTimeFormat(language, {
            dateStyle: 'medium',
            timeStyle: 'short',
          }).format(new Date(value))
        : unavailable,
    [language, unavailable],
  )
  const columns = useMemo<readonly DataTableColumn<AdminEvent>[]>(
    () => [
      {
        id: 'title',
        header: t('adminEvents.columns.title'),
        accessor: (event) => event.title_en ?? event.title_de ?? unavailable,
        cell: (event) => (
          <div className="space-y-1">
            <p className="font-medium">{event.title_en ?? event.title_de ?? unavailable}</p>
            {event.category ? (
              <p className="text-xs text-muted-foreground">{event.category}</p>
            ) : null}
          </div>
        ),
      },
      {
        id: 'schedule',
        header: t('adminEvents.columns.schedule'),
        accessor: (event) => event.start_date ?? '',
        cell: (event) => (
          <div className="space-y-1">
            <p>{formatDate(event.start_date)}</p>
            {event.end_date ? (
              <p className="text-xs text-muted-foreground">
                {t('adminEvents.ends', { date: formatDate(event.end_date) })}
              </p>
            ) : null}
          </div>
        ),
      },
      {
        id: 'status',
        header: t('adminEvents.columns.status'),
        accessor: (event) => event.status,
        cell: (event) => <EditorialBadge status={event.status} />,
      },
      {
        id: 'visibility',
        header: t('adminEvents.columns.visibility'),
        accessor: (event) => t(`adminEvents.visibility.${event.visibility}`),
      },
      {
        id: 'phase',
        header: t('adminEvents.columns.phase'),
        accessor: (event) => (event.phase ? t(`adminEvents.phase.${event.phase}`) : unavailable),
      },
      {
        id: 'updated',
        header: t('adminEvents.columns.updated'),
        accessor: (event) => event.updated_at,
        cell: (event) => formatDate(event.updated_at),
      },
      {
        id: 'actions',
        header: t('adminEvents.columns.actions'),
        cell: (event) => (
          <Button asChild variant="outline" size="sm">
            <Link to={`/admin/events/${event.id}/edit`}>
              {t('adminEvents.edit', { title: event.title_en ?? event.title_de ?? unavailable })}
            </Link>
          </Button>
        ),
      },
    ],
    [formatDate, t, unavailable],
  )

  const pendingSearch = searchInput.trim() !== search
  const loading = events.isPending || pendingSearch || isRecoveringPage
  const filtered = Boolean(search || status || visibility || phase || fromDate || toDate)
  const safeError =
    events.error instanceof ApiError && events.error.code === 'forbidden'
      ? t('adminEvents.forbidden')
      : t('adminEvents.error')
  const resetFilters = () => {
    setSearchInput('')
    setSearch('')
    setStatus(null)
    setVisibility(null)
    setPhase(null)
    setFromDate('')
    setToDate('')
    setPage(1)
  }

  return (
    <section aria-labelledby={titleId} className="min-w-0 space-y-6 py-6">
      <header className="flex min-w-0 flex-wrap items-start justify-between gap-4">
        <div className="space-y-2">
          <Typography
            as="h1"
            variant="h2"
            id={titleId}
            className="break-words text-3xl sm:text-4xl"
          >
            {t('adminEvents.title')}
          </Typography>
          <Typography variant="lead" className="max-w-3xl">
            {t('adminEvents.description')}
          </Typography>
        </div>
        <Button asChild>
          <Link to="/admin/events/new">
            <Plus aria-hidden="true" />
            {t('adminEvents.create')}
          </Link>
        </Button>
      </header>

      <div className="grid min-w-0 gap-3 rounded-lg border p-4 sm:grid-cols-2 xl:grid-cols-4">
        <div className="space-y-1 sm:col-span-2">
          <label htmlFor={searchId} className="text-sm font-medium">
            {t('adminEvents.filters.search')}
          </label>
          <div className="relative">
            <Search
              aria-hidden="true"
              className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground"
            />
            <input
              id={searchId}
              type="search"
              value={searchInput}
              placeholder={t('adminEvents.filters.searchPlaceholder')}
              className={`${controlClassName} w-full pl-10 pr-10`}
              onChange={(event) => setSearchInput(event.target.value)}
            />
            {searchInput ? (
              <Button
                type="button"
                variant="ghost"
                size="icon"
                className="absolute right-0 top-0"
                aria-label={t('adminEvents.filters.clearSearch')}
                onClick={() => setSearchInput('')}
              >
                <X aria-hidden="true" />
              </Button>
            ) : null}
          </div>
        </div>
        <label className="space-y-1 text-sm font-medium">
          {t('adminEvents.filters.status')}
          <select
            className={`${controlClassName} w-full`}
            value={status ?? ''}
            onChange={(event) => {
              setStatus((event.target.value || null) as EventStatus | null)
              setPage(1)
            }}
          >
            <option value="">{t('adminEvents.filters.all')}</option>
            <option value="DRAFT">{t('adminEvents.status.DRAFT')}</option>
            <option value="PUBLISHED">{t('adminEvents.status.PUBLISHED')}</option>
            <option value="CANCELLED">{t('adminEvents.status.CANCELLED')}</option>
          </select>
        </label>
        <label className="space-y-1 text-sm font-medium">
          {t('adminEvents.filters.visibility')}
          <select
            className={`${controlClassName} w-full`}
            value={visibility ?? ''}
            onChange={(event) => {
              setVisibility((event.target.value || null) as EventVisibility | null)
              setPage(1)
            }}
          >
            <option value="">{t('adminEvents.filters.all')}</option>
            <option value="PUBLIC">{t('adminEvents.visibility.PUBLIC')}</option>
            <option value="MEMBERS">{t('adminEvents.visibility.MEMBERS')}</option>
          </select>
        </label>
        <label className="space-y-1 text-sm font-medium">
          {t('adminEvents.filters.phase')}
          <select
            className={`${controlClassName} w-full`}
            value={phase ?? ''}
            onChange={(event) => {
              setPhase((event.target.value || null) as EventPhase | null)
              setPage(1)
            }}
          >
            <option value="">{t('adminEvents.filters.all')}</option>
            <option value="UPCOMING">{t('adminEvents.phase.UPCOMING')}</option>
            <option value="ONGOING">{t('adminEvents.phase.ONGOING')}</option>
            <option value="COMPLETED">{t('adminEvents.phase.COMPLETED')}</option>
          </select>
        </label>
        <label className="space-y-1 text-sm font-medium">
          {t('adminEvents.filters.from')}
          <input
            type="date"
            className={`${controlClassName} w-full`}
            value={fromDate}
            onChange={(event) => {
              setFromDate(event.target.value)
              setPage(1)
            }}
          />
        </label>
        <label className="space-y-1 text-sm font-medium">
          {t('adminEvents.filters.to')}
          <input
            type="date"
            className={`${controlClassName} w-full`}
            min={fromDate || undefined}
            value={toDate}
            onChange={(event) => {
              setToDate(event.target.value)
              setPage(1)
            }}
          />
        </label>
        <div className="flex items-end">
          <Button type="button" variant="outline" disabled={!filtered} onClick={resetFilters}>
            {t('adminEvents.filters.reset')}
          </Button>
        </div>
        {Boolean(fromDate) !== Boolean(toDate) ? (
          <p
            className="text-sm text-amber-700 dark:text-amber-300 sm:col-span-2 xl:col-span-4"
            role="status"
          >
            {t('adminEvents.filters.datePair')}
          </p>
        ) : null}
      </div>

      <DataTable
        data={isRecoveringPage ? [] : (events.data?.items ?? [])}
        columns={columns}
        getRowId={(event) => event.id}
        caption={t('adminEvents.caption')}
        searchable={false}
        isLoading={loading}
        error={events.isError && !pendingSearch ? safeError : null}
        onRetry={() => void events.refetch()}
        emptyMessage={filtered ? t('adminEvents.noResults') : t('adminEvents.empty')}
        pageSizeOptions={PAGE_SIZES}
        serverPagination={{
          page,
          pageSize,
          total: events.data?.total ?? 0,
          totalPages: events.data?.total_pages ?? 0,
          onPageChange: setPage,
          onPageSizeChange: (nextPageSize) => {
            setPageSize(nextPageSize)
            setPage(1)
          },
        }}
      />
    </section>
  )
}

export { AdminEventsPage }
