import { act, fireEvent, render, screen, within } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { DataTable, type DataTableColumn } from './data-table'
import i18n from '@/i18n'

type Row = { id: string; name: string; score: number; status: 'active' | 'pending' }
const data: readonly Row[] = [
  { id: 'a', name: 'Charlie', score: 100, status: 'active' },
  { id: 'b', name: 'Alice', score: 2, status: 'pending' },
  { id: 'c', name: 'Bob', score: 10, status: 'active' },
  { id: 'd', name: 'Dora', score: 20, status: 'pending' },
  { id: 'e', name: 'Eve', score: 30, status: 'active' },
]
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
  {
    id: 'actions',
    header: 'Actions',
    cell: (row) => <button type="button">Inspect {row.name}</button>,
  },
]
const props = {
  data,
  columns,
  caption: 'Fixture records',
  getRowId: (row: Row) => row.id,
  pageSizeOptions: [2, 3],
}
const bodyRows = () => screen.getByRole('table').querySelectorAll('tbody tr')
const names = () => [...bodyRows()].map((row) => row.firstElementChild?.textContent)
const click = (name: string) => fireEvent.click(screen.getByRole('button', { name }))

describe('ADMIN-004 reusable DataTable', () => {
  beforeEach(async () => {
    await i18n.changeLanguage('en')
  })

  it('renders caller cells in a native table, with caption, headers, unique controls and bounded paging', () => {
    render(<DataTable {...props} />)
    expect(screen.getByRole('table', { name: /Fixture records/ })).toHaveAttribute(
      'aria-busy',
      'false',
    )
    expect(screen.getAllByRole('columnheader')).toHaveLength(4)
    expect(screen.getByRole('columnheader', { name: 'Status' })).toHaveAttribute('scope', 'col')
    expect(screen.getByRole('searchbox', { name: 'Search table' })).toBeEnabled()
    expect(
      screen.getByRole('region', { name: 'Scrollable table: Fixture records' }),
    ).toHaveAttribute('tabindex', '0')
    expect(screen.getByRole('navigation', { name: 'Pagination: Fixture records' })).toBeVisible()
    expect(names()).toEqual(['Charlie', 'Alice'])
    expect(screen.getByRole('button', { name: 'Inspect Charlie' })).toBeVisible()
    expect(screen.getByText('Showing 1–2 of 5')).toBeVisible()
    expect(screen.getByRole('button', { name: 'Previous' })).toBeDisabled()
    click('Next')
    click('Next')
    expect(names()).toEqual(['Eve'])
    expect(screen.getByText('Page 3 of 3')).toBeVisible()
    expect(screen.getByText('Showing 5–5 of 5')).toBeVisible()
    expect(screen.getByRole('button', { name: 'Next' })).toBeDisabled()
    click('Previous')
    expect(names()).toEqual(['Bob', 'Dora'])
  })

  it('cycles ascending/descending/unsorted with aria-sort only on the active header', () => {
    render(<DataTable {...props} />)
    click('Sort Name ascending')
    expect(names()).toEqual(['Alice', 'Bob'])
    expect(
      screen.getByRole('button', { name: 'Sort Name descending' }).closest('th'),
    ).toHaveAttribute('aria-sort', 'ascending')
    click('Sort Name descending')
    expect(names()).toEqual(['Eve', 'Dora'])
    click('Clear sorting for Name')
    expect(names()).toEqual(['Charlie', 'Alice'])
    expect(screen.getByRole('table').querySelectorAll('[aria-sort]')).toHaveLength(0)
    click('Sort Name ascending')
    click('Sort Score ascending')
    expect(names()).toEqual(['Alice', 'Bob'])
    expect(screen.getByRole('table').querySelectorAll('[aria-sort]')).toHaveLength(1)
  })

  it('searches and filters the entire dataset before paginating and resets changes to page one', () => {
    render(<DataTable {...props} />)
    click('Next')
    click('Next')
    fireEvent.change(screen.getByRole('combobox', { name: 'Filter: Status' }), {
      target: { value: 'active' },
    })
    expect(names()).toEqual(['Charlie', 'Bob'])
    click('Next')
    expect(names()).toEqual(['Eve'])
    fireEvent.change(screen.getByRole('searchbox'), { target: { value: '  bOB ' } })
    expect(names()).toEqual(['Bob'])
    expect(screen.getByText('Showing 1–1 of 1')).toBeVisible()
    expect(screen.getByRole('button', { name: 'Next' })).toBeDisabled()
  })

  it('changing sort or page size resets paging, and Reset restores the source order/search/filters', () => {
    render(<DataTable {...props} />)
    click('Next')
    click('Sort Name ascending')
    expect(screen.getByText('Page 1 of 3')).toBeVisible()
    click('Next')
    fireEvent.change(screen.getByRole('combobox', { name: 'Rows per page' }), {
      target: { value: '3' },
    })
    expect(names()).toEqual(['Alice', 'Bob', 'Charlie'])
    expect(screen.getByText('Page 1 of 2')).toBeVisible()
    fireEvent.change(screen.getByRole('searchbox'), { target: { value: 'eve' } })
    fireEvent.change(screen.getByRole('combobox', { name: 'Filter: Status' }), {
      target: { value: 'active' },
    })
    click('Reset table')
    expect(names()).toEqual(['Charlie', 'Alice', 'Bob'])
    expect(screen.getByRole('searchbox')).toHaveValue('')
    expect(screen.getByRole('combobox', { name: 'Filter: Status' })).toHaveValue('')
    expect(screen.getByRole('button', { name: 'Reset table' })).toBeDisabled()
  })

  it('clamps a shrinking dataset and does not resurrect an old out-of-range page when it grows', () => {
    const { rerender } = render(<DataTable {...props} />)
    click('Next')
    click('Next')
    rerender(<DataTable {...props} data={data.slice(0, 3)} />)
    expect(names()).toEqual(['Bob'])
    expect(screen.getByText('Page 2 of 2')).toBeVisible()
    rerender(<DataTable {...props} />)
    expect(screen.getByText('Page 2 of 3')).toBeVisible()
    expect(names()).toEqual(['Bob', 'Dora'])
    rerender(<DataTable {...props} data={[]} />)
    expect(screen.getByText('No data available.')).toBeVisible()
    expect(screen.getByText('Page 0 of 0')).toBeVisible()
    expect(screen.getByRole('button', { name: 'Previous' })).toBeDisabled()
    expect(screen.getByRole('button', { name: 'Next' })).toBeDisabled()
  })

  it('distinguishes empty data from no search/filter results and allows recovery', () => {
    const { rerender } = render(
      <DataTable {...props} data={[]} emptyMessage="No fixture records yet." />,
    )
    expect(screen.getByText('No fixture records yet.')).toBeVisible()
    rerender(<DataTable {...props} />)
    fireEvent.change(screen.getByRole('searchbox'), { target: { value: 'absent' } })
    expect(screen.getByText('No results match your search or filters.')).toBeVisible()
    expect(screen.getByText('Showing 0–0 of 0')).toBeVisible()
    click('Reset table')
    expect(names()).toEqual(['Charlie', 'Alice'])
  })

  it('exposes caller loading/error/retry states without stale rows or invented totals', () => {
    const retry = vi.fn()
    const { rerender } = render(<DataTable {...props} isLoading />)
    expect(screen.getByRole('table')).toHaveAttribute('aria-busy', 'true')
    expect(screen.getByRole('status')).toHaveTextContent('Loading data…')
    expect(screen.queryByText('Charlie')).not.toBeInTheDocument()
    expect(screen.queryByText(/Showing/)).not.toBeInTheDocument()
    expect(screen.getByRole('searchbox')).toBeDisabled()
    rerender(<DataTable {...props} error="Records could not be loaded." onRetry={retry} />)
    expect(screen.getByRole('alert')).toHaveTextContent('Records could not be loaded.')
    expect(screen.getByRole('button', { name: 'Next' })).toBeDisabled()
    click('Try again')
    expect(retry).toHaveBeenCalledTimes(1)
    rerender(<DataTable {...props} />)
    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
    expect(names()).toEqual(['Charlie', 'Alice'])
  })

  it('omits a retry action when the caller does not supply one', () => {
    render(<DataTable {...props} error="Unavailable." />)
    expect(screen.getByRole('alert')).toHaveTextContent('Unavailable.')
    expect(screen.queryByRole('button', { name: 'Try again' })).not.toBeInTheDocument()
  })

  it('switches EN/DE copy without resetting query/filter/sort/page or localized column IDs', async () => {
    const { rerender } = render(<DataTable {...props} />)
    fireEvent.change(screen.getByRole('combobox', { name: 'Filter: Status' }), {
      target: { value: 'active' },
    })
    click('Sort Name ascending')
    click('Next')
    const table = screen.getByRole('table')
    await act(async () => {
      await i18n.changeLanguage('de')
    })
    const localized = columns.map((column) => ({
      ...column,
      header: column.id === 'score' ? 'Punkte' : column.header,
    }))
    rerender(<DataTable {...props} columns={localized} caption="Testdatensätze" />)
    expect(screen.getByRole('table')).toBe(table)
    expect(screen.getByRole('combobox', { name: 'Filter: Status' })).toHaveValue('active')
    expect(screen.getByText('Seite 2 von 2')).toBeVisible()
    expect(screen.getByText('3–3 von 3 angezeigt')).toBeVisible()
    expect(names()).toEqual(['Eve'])
    expect(
      screen.getByRole('button', { name: 'Name absteigend sortieren' }).closest('th'),
    ).toHaveAttribute('aria-sort', 'ascending')
    expect(screen.getByRole('searchbox', { name: 'Tabelle durchsuchen' })).toBeVisible()
    expect(screen.getByRole('button', { name: 'Zurück' })).toBeEnabled()
    expect(screen.getByRole('button', { name: 'Weiter' })).toBeDisabled()
  })

  it.each([
    ['empty', 'Keine Daten verfügbar.'],
    ['loading', 'Daten werden geladen…'],
    ['noResults', 'Keine Ergebnisse für Ihre Suche oder Filter.'],
  ] as const)('localizes the DE %s state', async (state, message) => {
    await i18n.changeLanguage('de')
    render(
      <DataTable {...props} data={state === 'empty' ? [] : data} isLoading={state === 'loading'} />,
    )
    if (state === 'noResults')
      fireEvent.change(screen.getByRole('searchbox'), { target: { value: 'absent' } })
    expect(screen.getByText(message)).toBeVisible()
  })

  it('supports multiple independent instances without duplicate labels, IDs or cross-table paging', () => {
    render(
      <>
        <DataTable {...props} />
        <DataTable {...props} caption="Other records" />
      </>,
    )
    const first = screen.getByRole('region', { name: 'Fixture records' })
    const second = screen.getByRole('region', { name: 'Other records' })
    expect(within(first).getByRole('searchbox').id).not.toBe(
      within(second).getByRole('searchbox').id,
    )
    fireEvent.click(within(first).getByRole('button', { name: 'Next' }))
    expect(within(first).getByText('Bob')).toBeVisible()
    expect(within(second).getByText('Charlie')).toBeVisible()
    fireEvent.change(within(second).getByRole('searchbox'), { target: { value: 'eve' } })
    expect(within(first).getByText('Page 2 of 3')).toBeVisible()
    expect(within(second).getByText('Eve')).toBeVisible()
  })

  it('keeps custom cell state attached to stable row IDs through sorting', () => {
    const stateful: readonly DataTableColumn<Row>[] = [
      columns[0],
      {
        id: 'note',
        header: 'Note',
        cell: (row) => <input aria-label={`Note ${row.id}`} defaultValue={row.name} />,
      },
    ]
    render(<DataTable {...props} columns={stateful} pageSizeOptions={[10]} />)
    fireEvent.change(screen.getByRole('textbox', { name: 'Note a' }), {
      target: { value: 'edited Charlie' },
    })
    click('Sort Name ascending')
    expect(screen.getByRole('textbox', { name: 'Note a' })).toHaveValue('edited Charlie')
    expect(screen.getByRole('textbox', { name: 'Note b' })).toHaveValue('Alice')
  })

  it('keeps empty-source messaging when only sort is active', () => {
    const { rerender } = render(<DataTable {...props} />)
    click('Sort Name ascending')
    rerender(<DataTable {...props} data={[]} />)
    expect(screen.getByText('No data available.')).toBeVisible()
    expect(screen.queryByText('No results match your search or filters.')).not.toBeInTheDocument()
  })

  it('synchronizes a removed page size without resurrecting it when options return', () => {
    const { rerender } = render(<DataTable {...props} />)
    fireEvent.change(screen.getByRole('combobox', { name: 'Rows per page' }), {
      target: { value: '3' },
    })
    rerender(<DataTable {...props} pageSizeOptions={[2]} />)
    expect(screen.getByRole('combobox', { name: 'Rows per page' })).toHaveValue('2')
    rerender(<DataTable {...props} />)
    expect(screen.getByRole('combobox', { name: 'Rows per page' })).toHaveValue('2')
  })

  it('handles metadata/page-size changes and disables search for cells without accessors', () => {
    const { rerender } = render(<DataTable {...props} initialPageSize={999} />)
    expect(screen.getByRole('combobox', { name: 'Rows per page' })).toHaveValue('2')
    fireEvent.change(screen.getByRole('combobox', { name: 'Filter: Status' }), {
      target: { value: 'active' },
    })
    click('Sort Name ascending')
    rerender(<DataTable {...props} columns={[columns[3]]} pageSizeOptions={[3]} />)
    expect(screen.queryByRole('searchbox')).not.toBeInTheDocument()
    expect(screen.queryByRole('combobox', { name: 'Filter: Status' })).not.toBeInTheDocument()
    expect(screen.getAllByRole('button', { name: /Inspect/ })).toHaveLength(3)
    expect(screen.getByRole('combobox', { name: 'Rows per page' })).toHaveValue('3')
  })
})
