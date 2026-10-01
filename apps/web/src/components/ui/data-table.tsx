import { useId, useMemo, useState } from 'react'
import { ArrowDown, ArrowUp, ArrowUpDown } from 'lucide-react'
import { useTranslation } from 'react-i18next'

import { Button } from '@/components/ui/button'
import {
  canSort,
  defaultPageSizes,
  getDataTableRows,
  normalizePageSizes,
  valueText,
  type DataTableColumn,
  type DataTableSort,
} from '@/components/ui/data-table-model'
import { cn } from '@/lib/utils'

interface DataTableProps<T> {
  /** Complete client-side dataset. Server pagination belongs to the caller's API layer. */
  data: readonly T[]
  columns: readonly DataTableColumn<T>[]
  getRowId: (row: T) => string
  caption: string
  pageSizeOptions?: readonly number[]
  initialPageSize?: number
  searchable?: boolean
  isLoading?: boolean
  /** A safe, localized public message, not an unfiltered backend exception. */
  error?: string | null
  onRetry?: () => void
  emptyMessage?: string
  /** Optional server-owned pagination. `data` must contain only the current page. */
  serverPagination?: {
    page: number
    pageSize: number
    total: number
    totalPages: number
    onPageChange: (page: number) => void
    onPageSizeChange?: (pageSize: number) => void
  }
}

const controlClassName =
  'h-10 w-full min-w-0 rounded-md border border-input bg-background px-3 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50'

function DataTable<T>({
  data,
  columns,
  getRowId,
  caption,
  pageSizeOptions = defaultPageSizes,
  initialPageSize,
  searchable = true,
  isLoading = false,
  error,
  onRetry,
  emptyMessage,
  serverPagination,
}: DataTableProps<T>) {
  const { t, i18n } = useTranslation()
  const id = useId()
  const language = i18n.resolvedLanguage ?? 'en'
  const sizes = useMemo(() => normalizePageSizes(pageSizeOptions), [pageSizeOptions])
  const [query, setQuery] = useState('')
  const [filters, setFilters] = useState<Record<string, string>>({})
  const [sort, setSort] = useState<DataTableSort>(null)
  const [pageSize, setPageSize] = useState(() =>
    initialPageSize && sizes.includes(initialPageSize) ? initialPageSize : sizes[0],
  )
  const [pageIndex, setPageIndex] = useState(0)
  const localSize = sizes.includes(pageSize) ? pageSize : sizes[0]
  if (!serverPagination && pageSize !== localSize) setPageSize(localSize)
  const size = serverPagination?.pageSize ?? localSize
  const hasSearch =
    searchable && columns.some((column) => column.accessor && column.searchable !== false)
  const filterColumns = columns.filter(
    (column) => column.filterOptions?.length && (column.accessor || column.filterValue),
  )
  const rows = useMemo(
    () =>
      getDataTableRows(data, columns, { query: hasSearch ? query : '', filters, sort }, language),
    [data, columns, query, hasSearch, filters, sort, language],
  )
  const pageCount = serverPagination
    ? Math.max(1, serverPagination.totalPages)
    : Math.max(1, Math.ceil(rows.length / size))
  const page = serverPagination ? serverPagination.page : Math.min(pageIndex, pageCount - 1)
  // Synchronize only when dataset/options shrink the range, before rendering child rows.
  // This avoids an effect and prevents an old out-of-range page returning when rows grow again.
  if (!serverPagination && pageIndex !== page) setPageIndex(page)
  const start = serverPagination ? (page - 1) * size : page * size
  const pageRows = serverPagination ? rows : rows.slice(start, start + size)
  const unavailable = isLoading || Boolean(error)
  const activeFilters = filterColumns.some((column) =>
    column.filterOptions?.some((option) => option.value === filters[column.id]),
  )
  const hasConstraints = Boolean((hasSearch && query.trim()) || activeFilters)
  const hasView = Boolean((hasSearch && query) || activeFilters || sort)

  const changeSort = (column: DataTableColumn<T>) => {
    setSort((current) =>
      current?.columnId !== column.id
        ? { columnId: column.id, direction: 'ascending' }
        : current.direction === 'ascending'
          ? { columnId: column.id, direction: 'descending' }
          : null,
    )
    setPageIndex(0)
  }

  return (
    <section aria-label={caption} className="min-w-0 space-y-4">
      <div className="flex min-w-0 flex-wrap items-end gap-3">
        {hasSearch ? (
          <div className="min-w-0 flex-[1_1_16rem] space-y-1">
            <label htmlFor={`${id}-search`} className="text-sm font-medium">
              {t('dataTable.search')}
            </label>
            <input
              id={`${id}-search`}
              type="search"
              value={query}
              disabled={unavailable}
              className={controlClassName}
              onChange={(event) => {
                setQuery(event.target.value)
                setPageIndex(0)
              }}
            />
          </div>
        ) : null}
        {filterColumns.map((column) => (
          <div key={column.id} className="min-w-0 flex-[1_1_10rem] space-y-1">
            <label
              htmlFor={`${id}-filter-${column.id}`}
              className="text-sm font-medium break-words"
            >
              {t('dataTable.filter', { column: column.header })}
            </label>
            <select
              id={`${id}-filter-${column.id}`}
              disabled={unavailable}
              value={
                column.filterOptions?.some((option) => option.value === filters[column.id])
                  ? filters[column.id]
                  : ''
              }
              className={controlClassName}
              onChange={(event) => {
                setFilters((current) => ({ ...current, [column.id]: event.target.value }))
                setPageIndex(0)
              }}
            >
              <option value="">{t('dataTable.all')}</option>
              {column.filterOptions?.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </div>
        ))}
        {hasSearch || filterColumns.length ? (
          <Button
            type="button"
            variant="outline"
            disabled={unavailable || !hasView}
            onClick={() => {
              setQuery('')
              setFilters({})
              setSort(null)
              setPageIndex(0)
            }}
            className="h-auto min-h-10 max-w-full whitespace-normal break-words"
          >
            {t('dataTable.reset')}
          </Button>
        ) : null}
      </div>
      <div
        role="region"
        aria-label={t('dataTable.scrollRegion', { caption })}
        tabIndex={0}
        className="max-w-full min-w-0 overflow-x-auto rounded-md border focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
      >
        <table aria-busy={isLoading} className="w-full min-w-[32rem] text-sm">
          <caption className="caption-top px-4 py-3 text-left font-medium break-words">
            {caption}
            {columns.some(canSort) ? (
              <span className="sr-only"> {t('dataTable.sortHint')}</span>
            ) : null}
          </caption>
          <thead className="border-b bg-muted/50">
            <tr>
              {columns.map((column) => {
                const direction =
                  sort?.columnId === column.id && canSort(column) ? sort.direction : undefined
                const Icon =
                  direction === 'ascending'
                    ? ArrowUp
                    : direction === 'descending'
                      ? ArrowDown
                      : ArrowUpDown
                const next =
                  direction === 'ascending'
                    ? 'sortDescending'
                    : direction === 'descending'
                      ? 'clearSort'
                      : 'sortAscending'
                return (
                  <th
                    key={column.id}
                    scope="col"
                    aria-sort={direction}
                    className="px-4 py-2 text-left font-medium"
                  >
                    {canSort(column) ? (
                      <Button
                        type="button"
                        variant="ghost"
                        size="sm"
                        disabled={unavailable}
                        aria-label={t(`dataTable.${next}`, { column: column.header })}
                        onClick={() => changeSort(column)}
                        className="h-auto min-h-9 justify-start whitespace-normal text-left"
                      >
                        {column.header}
                        <Icon aria-hidden="true" className="size-4 shrink-0" />
                      </Button>
                    ) : (
                      column.header
                    )}
                  </th>
                )
              })}
            </tr>
          </thead>
          <tbody>
            {unavailable || !rows.length ? (
              <tr>
                <td colSpan={Math.max(1, columns.length)} className="px-4 py-8 text-center">
                  {isLoading ? (
                    <p role="status">{t('dataTable.loading')}</p>
                  ) : error ? (
                    <div className="space-y-3">
                      <p role="alert">{error}</p>
                      {onRetry ? (
                        <Button type="button" variant="outline" onClick={onRetry}>
                          {t('dataTable.retry')}
                        </Button>
                      ) : null}
                    </div>
                  ) : (
                    <p role="status">
                      {hasConstraints
                        ? t('dataTable.noResults')
                        : (emptyMessage ?? t('dataTable.empty'))}
                    </p>
                  )}
                </td>
              </tr>
            ) : (
              pageRows.map((row) => (
                <tr key={getRowId(row)} className="border-b last:border-0 hover:bg-muted/30">
                  {columns.map((column) => (
                    <td key={column.id} className="max-w-sm px-4 py-3 align-top break-words">
                      {column.cell ? column.cell(row) : valueText(column.accessor?.(row))}
                    </td>
                  ))}
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
      <div className="flex min-w-0 flex-wrap items-center justify-between gap-3">
        {!unavailable ? (
          <p role="status" aria-live="polite" className="text-sm text-muted-foreground">
            {t('dataTable.results', {
              from: pageRows.length ? start + 1 : 0,
              to: pageRows.length ? start + pageRows.length : 0,
              total: serverPagination?.total ?? rows.length,
            })}
          </p>
        ) : null}
        <div className="flex min-w-0 flex-wrap items-center gap-2">
          <label htmlFor={`${id}-size`} className="text-sm">
            {t('dataTable.pageSize')}
          </label>
          <select
            id={`${id}-size`}
            value={size}
            disabled={
              unavailable || Boolean(serverPagination && !serverPagination.onPageSizeChange)
            }
            className={cn(controlClassName, 'w-20')}
            onChange={(event) => {
              const nextSize = Number(event.target.value)
              if (serverPagination) serverPagination.onPageSizeChange?.(nextSize)
              else {
                setPageSize(nextSize)
                setPageIndex(0)
              }
            }}
          >
            {sizes.map((option) => (
              <option key={option} value={option}>
                {option}
              </option>
            ))}
          </select>
        </div>
        <nav
          aria-label={t('dataTable.pagination', { caption })}
          className="flex min-w-0 flex-wrap items-center gap-2"
        >
          <Button
            type="button"
            variant="outline"
            size="sm"
            disabled={unavailable || page <= (serverPagination ? 1 : 0)}
            onClick={() =>
              serverPagination ? serverPagination.onPageChange(page - 1) : setPageIndex(page - 1)
            }
          >
            {t('dataTable.previous')}
          </Button>
          {!unavailable ? (
            <span className="text-sm">
              {t('dataTable.page', {
                current:
                  (serverPagination?.total ?? rows.length) ? page + (serverPagination ? 0 : 1) : 0,
                total: (serverPagination?.total ?? rows.length) ? pageCount : 0,
              })}
            </span>
          ) : null}
          <Button
            type="button"
            variant="outline"
            size="sm"
            disabled={unavailable || page >= pageCount - (serverPagination ? 0 : 1)}
            onClick={() =>
              serverPagination ? serverPagination.onPageChange(page + 1) : setPageIndex(page + 1)
            }
          >
            {t('dataTable.next')}
          </Button>
        </nav>
      </div>
    </section>
  )
}

export { DataTable }
export type { DataTableProps }
export type { DataTableColumn, DataTableFilterOption } from '@/components/ui/data-table-model'
