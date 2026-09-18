import type { ReactNode } from 'react'

type DataTableValue = string | number | boolean | null | undefined
type DataTableSort = { columnId: string; direction: 'ascending' | 'descending' } | null

interface DataTableFilterOption {
  value: string
  label: string
}

interface DataTableColumn<T> {
  /** Unique, stable ID; independent of the localized header. */
  id: string
  header: string
  /** Plain value used for search, sort, filters and default cell rendering. */
  accessor?: (row: T) => DataTableValue
  cell?: (row: T) => ReactNode
  sortable?: boolean
  compare?: (left: T, right: T) => number
  /** Accessor columns are searchable by default; action cells can opt out. */
  searchable?: boolean
  filterOptions?: readonly DataTableFilterOption[]
  filterValue?: (row: T) => string
}

interface DataTableView {
  query: string
  filters: Readonly<Record<string, string>>
  sort: DataTableSort
}

const defaultPageSizes = [10, 25, 50] as const

function normalizePageSizes(options: readonly number[]): number[] {
  const valid = [...new Set(options.filter((size) => Number.isSafeInteger(size) && size > 0))]
  return valid.length ? valid : [...defaultPageSizes]
}

function valueText(value: DataTableValue): string {
  return value == null || (typeof value === 'number' && !Number.isFinite(value))
    ? ''
    : String(value)
}

function canSort<T>(column: DataTableColumn<T>): boolean {
  return Boolean(column.sortable && (column.accessor || column.compare))
}

function getDataTableRows<T>(
  data: readonly T[],
  columns: readonly DataTableColumn<T>[],
  view: DataTableView,
  language: string,
): T[] {
  const normalize = (value: string) => value.normalize('NFKC').toLocaleLowerCase(language)
  const query = normalize(view.query.trim())
  const searchable = columns.filter((column) => column.accessor && column.searchable !== false)
  const filters = columns.filter(
    (column) =>
      column.filterOptions?.some((option) => option.value === view.filters[column.id]) &&
      (column.filterValue || column.accessor),
  )
  const rows = data.filter(
    (row) =>
      (!query ||
        searchable.some((column) =>
          normalize(valueText(column.accessor?.(row))).includes(query),
        )) &&
      filters.every(
        (column) =>
          (column.filterValue?.(row) ?? valueText(column.accessor?.(row))) ===
          view.filters[column.id],
      ),
  )
  const sort = view.sort
  const column = columns.find((candidate) => candidate.id === sort?.columnId && canSort(candidate))
  if (!sort || !column) return rows

  const collator = new Intl.Collator(language, { numeric: true, sensitivity: 'base' })
  const direction = sort.direction === 'ascending' ? 1 : -1
  return rows.sort((left, right) => {
    if (column.compare) return direction * column.compare(left, right)
    const a = column.accessor?.(left)
    const b = column.accessor?.(right)
    const aMissing = a == null || (typeof a === 'number' && !Number.isFinite(a))
    const bMissing = b == null || (typeof b === 'number' && !Number.isFinite(b))
    // Missing values remain last in both directions; equal values retain input order.
    if (aMissing || bMissing) return Number(aMissing) - Number(bMissing)
    const result =
      typeof a === 'number' && typeof b === 'number'
        ? a - b
        : collator.compare(valueText(a), valueText(b))
    return direction * result
  })
}

export { canSort, defaultPageSizes, getDataTableRows, normalizePageSizes, valueText }
export type { DataTableColumn, DataTableFilterOption, DataTableSort, DataTableValue, DataTableView }
