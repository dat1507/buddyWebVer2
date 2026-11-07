import { useEffect, useId, useRef, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { RefreshCw } from 'lucide-react'
import { useTranslation } from 'react-i18next'

import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { DataTable } from '@/components/ui/data-table'
import { Typography } from '@/components/ui/typography'
import {
  adminAuditClient,
  auditCategories,
  auditPeriods,
  type AuditActivity,
  type AuditActor,
  type AuditCategory,
  type AuditPeriod,
} from '@/features/admin-audit-log'
import { useAuthStore } from '@/stores/auth-store'

const filterClass =
  'min-h-11 w-full min-w-0 rounded-md border border-input bg-background px-3 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring'

function AuditDetails({
  title,
  fields,
  onClose,
}: {
  title: string
  fields: ReadonlyArray<readonly [string, string]>
  onClose: () => void
}) {
  const { t } = useTranslation()
  const label = useId()
  const dialog = useRef<HTMLDialogElement>(null)
  const close = useRef<HTMLButtonElement>(null)

  useEffect(() => {
    const element = dialog.current
    if (!element) return
    const opener = document.activeElement
    element.showModal()
    close.current?.focus()
    return () => {
      element.close()
      if (opener instanceof HTMLElement && opener.isConnected) opener.focus()
    }
  }, [])

  return (
    <dialog
      ref={dialog}
      aria-labelledby={label}
      onCancel={(event) => {
        event.preventDefault()
        onClose()
      }}
      className="max-h-[85dvh] w-[calc(100%-2rem)] max-w-lg overflow-y-auto rounded-xl border border-border bg-background p-5 text-foreground backdrop:bg-black/65"
    >
      <Typography as="h2" variant="h4" id={label}>
        {title}
      </Typography>
      <dl className="my-4 grid gap-3 break-words">
        {fields.map(([term, value]) => (
          <div key={term}>
            <dt className="text-sm font-semibold">{term}</dt>
            <dd className="text-sm text-muted-foreground">{value}</dd>
          </div>
        ))}
      </dl>
      <Button ref={close} variant="outline" className="min-h-11" onClick={onClose}>
        {t('auditLog.close')}
      </Button>
    </dialog>
  )
}

export function AdminAuditLogPage() {
  const { t, i18n } = useTranslation()
  const userId = useAuthStore((state) => state.user?.id)
  const [page, setPage] = useState(1)
  const [actorPage, setActorPage] = useState(1)
  const [actor, setActor] = useState<AuditActor | null>(null)
  const [category, setCategory] = useState<AuditCategory | ''>('')
  const [period, setPeriod] = useState<AuditPeriod>('month')
  const [start, setStart] = useState('')
  const [end, setEnd] = useState('')
  const [selected, setSelected] = useState<AuditActivity | null>(null)

  const span = Date.parse(end) - Date.parse(start)
  const validRange =
    period !== 'custom' ||
    (start >= '2000-01-01' &&
      /^\d{4}-\d{2}-\d{2}$/.test(start) &&
      /^\d{4}-\d{2}-\d{2}$/.test(end) &&
      span >= 0 &&
      span < 366 * 86_400_000)
  const params = new URLSearchParams({ page: String(page), period })
  if (actor) params.set('admin_id', actor.id)
  if (category) params.set('category', category)
  if (period === 'custom') {
    params.set('start', start)
    params.set('end', end)
  }

  const audit = useQuery({
    queryKey: ['private', userId, 'audit-log', params.toString()],
    queryFn: ({ signal }) => adminAuditClient.list(params, signal),
    enabled: Boolean(userId) && validRange,
    meta: { private: true },
    refetchOnWindowFocus: false,
    refetchOnReconnect: false,
  })
  const actors = useQuery({
    queryKey: ['private', userId, 'audit-log-actors', actorPage],
    queryFn: ({ signal }) => adminAuditClient.actors(actorPage, signal),
    enabled: Boolean(userId),
    meta: { private: true },
    refetchOnWindowFocus: false,
    refetchOnReconnect: false,
  })

  const formatter = new Intl.DateTimeFormat(i18n.resolvedLanguage, {
    dateStyle: 'medium',
    timeStyle: 'medium',
    timeZone: 'Asia/Ho_Chi_Minh',
  })
  const timeLabel = (row: AuditActivity) => formatter.format(new Date(row.created_at)) + ' (GMT+7)'
  const actorLabel = (row: AuditActivity) =>
    row.admin_email ?? t('auditLog.historicalAdmin', { id: row.admin_id })
  const actionLabel = (row: AuditActivity) =>
    t('auditLog.actions.' + row.action.replaceAll('.', '_'), {
      defaultValue: t('auditLog.activity'),
    })
  const options = actors.data?.items ?? []
  const actorOptions =
    actor && !options.some((option) => option.id === actor.id) ? [actor, ...options] : options

  return (
    <section className="min-w-0 space-y-5 py-6">
      <header className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <Typography as="h1" variant="h3">
            {t('auditLog.title')}
          </Typography>
          <Typography variant="muted">{t('auditLog.description')}</Typography>
        </div>
        <Button
          variant="outline"
          className="min-h-11"
          disabled={!validRange || audit.isFetching}
          onClick={() => {
            void audit.refetch()
            void actors.refetch()
          }}
        >
          <RefreshCw aria-hidden="true" />
          {t('auditLog.refresh')}
        </Button>
      </header>

      <Card className="grid min-w-0 gap-3 p-4 sm:grid-cols-3">
        <div className="min-w-0">
          <label className="block space-y-1 text-sm">
            <span>{t('auditLog.admin')}</span>
            <select
              className={filterClass}
              value={actor?.id ?? ''}
              onChange={(event) => {
                setActor(actorOptions.find((option) => option.id === event.target.value) ?? null)
                setPage(1)
              }}
            >
              <option value="">{t('auditLog.allAdmins')}</option>
              {actorOptions.map((option) => (
                <option key={option.id} value={option.id}>
                  {option.email}
                </option>
              ))}
            </select>
          </label>
          {actors.isLoading && (
            <p role="status" className="text-sm">
              {t('auditLog.loadingActors')}
            </p>
          )}
          {actors.isError && (
            <Button
              variant="outline"
              className="mt-2 min-h-11"
              onClick={() => void actors.refetch()}
            >
              {t('auditLog.retryActors')}
            </Button>
          )}
          {(actorPage > 1 || actors.data?.has_more) && (
            <div className="mt-2 flex flex-wrap gap-2">
              <Button
                variant="outline"
                className="min-h-11"
                disabled={actorPage === 1}
                onClick={() => setActorPage(actorPage - 1)}
              >
                {t('auditLog.previousAdmins')}
              </Button>
              <Button
                variant="outline"
                className="min-h-11"
                disabled={!actors.data?.has_more}
                onClick={() => setActorPage(actorPage + 1)}
              >
                {t('auditLog.moreAdmins')}
              </Button>
            </div>
          )}
        </div>
        <label className="min-w-0 space-y-1 text-sm">
          <span>{t('auditLog.category')}</span>
          <select
            className={filterClass}
            value={category}
            onChange={(event) => {
              setCategory(event.target.value as AuditCategory | '')
              setPage(1)
            }}
          >
            <option value="">{t('auditLog.allActivities')}</option>
            {auditCategories.map((value) => (
              <option key={value} value={value}>
                {t('auditLog.categories.' + value)}
              </option>
            ))}
          </select>
        </label>
        <label className="min-w-0 space-y-1 text-sm">
          <span>{t('auditLog.period')}</span>
          <select
            className={filterClass}
            value={period}
            onChange={(event) => {
              setPeriod(event.target.value as AuditPeriod)
              setPage(1)
            }}
          >
            {auditPeriods.map((value) => (
              <option key={value} value={value}>
                {t('auditLog.periods.' + value)}
              </option>
            ))}
          </select>
        </label>
        {period === 'custom' && (
          <>
            <label className="min-w-0 space-y-1 text-sm">
              <span>{t('auditLog.from')}</span>
              <input
                type="date"
                className={filterClass}
                value={start}
                onChange={(event) => {
                  setStart(event.target.value)
                  setPage(1)
                }}
              />
            </label>
            <label className="min-w-0 space-y-1 text-sm">
              <span>{t('auditLog.to')}</span>
              <input
                type="date"
                className={filterClass}
                value={end}
                onChange={(event) => {
                  setEnd(event.target.value)
                  setPage(1)
                }}
              />
            </label>
          </>
        )}
      </Card>

      {!validRange ? (
        <p role="status">{t('auditLog.invalidRange')}</p>
      ) : (
        <DataTable
          caption={t('auditLog.history')}
          data={audit.data?.items ?? []}
          getRowId={(row) => row.id}
          searchable={false}
          pageSizeOptions={[20]}
          isLoading={audit.isLoading}
          error={audit.isError ? t('auditLog.error') : null}
          onRetry={() => void audit.refetch()}
          emptyMessage={t('auditLog.empty')}
          serverPagination={{
            page,
            pageSize: 20,
            total: audit.data?.total ?? 0,
            totalPages: audit.data?.total_pages ?? 0,
            onPageChange: setPage,
          }}
          columns={[
            { id: 'when', header: t('auditLog.when'), cell: timeLabel },
            { id: 'actor', header: t('auditLog.admin'), cell: actorLabel },
            { id: 'action', header: t('auditLog.action'), cell: actionLabel },
            {
              id: 'where',
              header: t('auditLog.module'),
              cell: (row) => t('auditLog.categories.' + row.category),
            },
            {
              id: 'details',
              header: t('auditLog.details'),
              cell: (row) => (
                <Button
                  variant="outline"
                  size="sm"
                  className="min-h-11"
                  onClick={() => setSelected(row)}
                  aria-label={t('auditLog.detailsFor', {
                    action: actionLabel(row),
                    actor: actorLabel(row),
                    time: timeLabel(row),
                  })}
                >
                  {t('auditLog.viewDetails')}
                </Button>
              ),
            },
          ]}
        />
      )}
      {selected && (
        <AuditDetails
          title={t('auditLog.details')}
          onClose={() => setSelected(null)}
          fields={[
            [t('auditLog.action'), actionLabel(selected)],
            [t('auditLog.admin'), actorLabel(selected)],
            [t('auditLog.when'), timeLabel(selected)],
            [t('auditLog.category'), t('auditLog.categories.' + selected.category)],
            [t('auditLog.resource'), t('auditLog.resources.' + selected.resource_type)],
            ...(selected.resource_id
              ? [[t('auditLog.reference'), selected.resource_id] as const]
              : []),
            ...(selected.before_status
              ? [[t('auditLog.before'), t('auditLog.statuses.' + selected.before_status)] as const]
              : []),
            ...(selected.after_status
              ? [[t('auditLog.after'), t('auditLog.statuses.' + selected.after_status)] as const]
              : []),
            ...(!selected.resource_id && !selected.before_status && !selected.after_status
              ? [[t('auditLog.additional'), t('auditLog.noDetails')] as const]
              : []),
          ]}
        />
      )}
    </section>
  )
}
