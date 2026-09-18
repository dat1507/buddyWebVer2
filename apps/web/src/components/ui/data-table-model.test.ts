import { describe, expect, it } from 'vitest'

import { getDataTableRows, normalizePageSizes, type DataTableColumn } from './data-table-model'

type Row = { id: string; name: string; score: number | null; status: string; internal: string }
const data: readonly Row[] = Object.freeze([
  { id: 'a', name: 'Student 10', score: 100, status: 'active', internal: 'private-search-marker' },
  { id: 'b', name: 'Student 2', score: 9, status: 'pending', internal: 'private-search-marker' },
  { id: 'c', name: 'STUDENT 1', score: 9, status: 'active', internal: 'private-search-marker' },
  { id: 'd', name: 'Änne', score: null, status: 'pending', internal: 'private-search-marker' },
])
const columns: readonly DataTableColumn<Row>[] = [
  { id: 'name', header: 'Name', accessor: (row) => row.name, sortable: true },
  { id: 'score', header: 'Score', accessor: (row) => row.score, sortable: true },
  {
    id: 'status',
    header: 'Status',
    accessor: (row) => row.status,
    filterOptions: [
      { value: 'active', label: 'Active' },
      { value: 'pending', label: 'Pending' },
    ],
  },
  { id: 'internal', header: 'Internal', accessor: (row) => row.internal, searchable: false },
]
const ids = (rows: readonly Row[]) => rows.map((row) => row.id)

describe('ADMIN-004 client-side table processing', () => {
  it('searches visible accessor values case-insensitively, trims and combines with exact filters', () => {
    const result = getDataTableRows(
      data,
      columns,
      {
        query: '  STUDENT ',
        filters: { status: 'active' },
        sort: { columnId: 'score', direction: 'ascending' },
      },
      'en',
    )
    expect(ids(result)).toEqual(['c', 'a'])
    expect(ids(data)).toEqual(['a', 'b', 'c', 'd'])
  })

  it('does not search excluded fields or React action cell content', () => {
    const actionColumn = { id: 'action', header: 'Action', cell: () => 'hidden-action-marker' }
    for (const query of ['private-search-marker', 'hidden-action-marker']) {
      expect(
        getDataTableRows(
          data,
          [...columns, actionColumn],
          { query, filters: {}, sort: null },
          'en',
        ),
      ).toEqual([])
    }
  })

  it.each(['ascending', 'descending'] as const)(
    'sorts numeric values %s with nulls last and stable equal rows',
    (direction) => {
      const result = getDataTableRows(
        data,
        columns,
        { query: '', filters: {}, sort: { columnId: 'score', direction } },
        'en',
      )
      expect(ids(result)).toEqual(
        direction === 'ascending' ? ['b', 'c', 'a', 'd'] : ['a', 'b', 'c', 'd'],
      )
    },
  )

  it('sorts strings naturally rather than ordering Student 10 before Student 2', () => {
    const result = getDataTableRows(
      data.slice(0, 3),
      columns,
      { query: '', filters: {}, sort: { columnId: 'name', direction: 'ascending' } },
      'de',
    )
    expect(ids(result)).toEqual(['c', 'b', 'a'])
  })

  it('supports independent canonical filter values and custom comparators', () => {
    const custom: readonly DataTableColumn<Row>[] = [
      {
        id: 'name',
        header: 'Name',
        accessor: (row) => row.name,
        sortable: true,
        compare: (a, b) => a.name.length - b.name.length,
        filterOptions: [{ value: 'active', label: 'Active' }],
        filterValue: (row) => row.status,
      },
    ]
    const result = getDataTableRows(
      data,
      custom,
      {
        query: '',
        filters: { name: 'active' },
        sort: { columnId: 'name', direction: 'ascending' },
      },
      'en',
    )
    expect(ids(result)).toEqual(['c', 'a'])
  })

  it('ignores removed/unsupported sort and filter descriptors after metadata changes', () => {
    const result = getDataTableRows(
      data,
      columns,
      {
        query: '',
        filters: { status: 'removed-option', removed: 'active' },
        sort: { columnId: 'internal', direction: 'ascending' },
      },
      'en',
    )
    expect(ids(result)).toEqual(ids(data))
  })

  it('searches normalized Unicode and numeric/boolean values without null or non-finite markers', () => {
    const values = [
      { id: 'a', value: 'Ａnne' },
      { id: 'b', value: 42 },
      { id: 'c', value: false },
      { id: 'd', value: Number.NaN },
      { id: 'e', value: undefined },
    ]
    const valueColumns: readonly DataTableColumn<(typeof values)[number]>[] = [
      { id: 'value', header: 'Value', accessor: (row) => row.value },
    ]
    for (const [query, expected] of [
      ['anne', ['a']],
      ['42', ['b']],
      ['false', ['c']],
      ['nan', []],
      ['undefined', []],
    ] as const) {
      expect(
        getDataTableRows(values, valueColumns, { query, filters: {}, sort: null }, 'en').map(
          (row) => row.id,
        ),
      ).toEqual(expected)
    }
  })

  it('combines multiple column filters using AND rather than accepting either match', () => {
    const extra: DataTableColumn<Row> = {
      id: 'scoreFilter',
      header: 'Score',
      accessor: (row) => row.score,
      filterOptions: [{ value: '9', label: 'Nine' }],
    }
    const result = getDataTableRows(
      data,
      [...columns, extra],
      { query: 'student', filters: { status: 'active', scoreFilter: '9' }, sort: null },
      'en',
    )
    expect(ids(result)).toEqual(['c'])
  })

  it('normalizes page options to unique positive safe integers and uses a valid fallback', () => {
    expect(normalizePageSizes([25, 0, 25, -1, 2.5, Infinity, 10])).toEqual([25, 10])
    expect(normalizePageSizes([])).toEqual([10, 25, 50])
  })
})
