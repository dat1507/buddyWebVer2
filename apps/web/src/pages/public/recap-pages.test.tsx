import '@/i18n'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import * as api from '@/features/recaps/recaps'
import { RecapGalleryPage } from './recap-pages'
vi.mock('@/features/recaps/recap-photo', () => ({ RecapImage: () => <img alt="Campus" /> }))
const record: api.Recap = {
  id: '11111111-1111-4111-8111-111111111111',
  related_event_id: null,
  title_en: 'Welcome',
  title_de: 'Willkommen',
  summary_en: 'Our day',
  summary_de: 'Unser Tag',
  editorial_en: null,
  editorial_de: null,
  event_date: null,
  status: 'PUBLISHED',
  version: 1,
  thumbnail_id: null,
  cleanup_pending: false,
  photos: [],
}
function mount() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false, gcTime: 0 } } })
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter>
        <RecapGalleryPage />
      </MemoryRouter>
    </QueryClientProvider>,
  )
}
describe('Dynamic public recap gallery', () => {
  beforeEach(() => vi.restoreAllMocks())
  it('uses a text hero and an honest empty state without fake photos', async () => {
    vi.spyOn(api, 'fetchRecaps').mockResolvedValue({
      items: [],
      mosaic: [],
      years: [],
      page: 1,
      total: 0,
      total_pages: 0,
      pending_cleanup: [],
    })
    mount()
    expect(await screen.findByText('Our next chapter starts here')).toBeInTheDocument()
    expect(screen.queryByRole('img')).toBeNull()
    expect(screen.getByRole('link', { name: 'Back to Events' })).toHaveAttribute('href', '/#events')
  })
  it('loads a second nine-card page and resets pagination when a year is selected', async () => {
    const list = vi.spyOn(api, 'fetchRecaps').mockImplementation(async (page) => ({
      items:
        page === 1
          ? Array.from({ length: 9 }, (_, index) => ({
              ...record,
              id: `11111111-1111-4111-8111-11111111111${index}`,
            }))
          : [{ ...record, title_en: 'Older memory' }],
      mosaic: [],
      years: [2026, 2025],
      page,
      total: 10,
      total_pages: 2,
      pending_cleanup: [],
    }))
    mount()
    await waitFor(() => expect(screen.getAllByRole('article')).toHaveLength(9))
    fireEvent.click(screen.getByRole('button', { name: 'Next' }))
    expect(await screen.findByRole('heading', { name: 'Older memory' })).toBeInTheDocument()
    fireEvent.change(screen.getByRole('combobox', { name: 'Year' }), { target: { value: '2025' } })
    await waitFor(() =>
      expect(list).toHaveBeenLastCalledWith(1, '2025', false, expect.any(AbortSignal)),
    )
  })
  it('shows a recoverable API outage', async () => {
    vi.spyOn(api, 'fetchRecaps').mockRejectedValue(new Error('local injected outage'))
    mount()
    expect(await screen.findByRole('alert')).toHaveTextContent('temporarily unavailable')
    expect(screen.getByRole('button', { name: 'Try again' })).toBeInTheDocument()
  })
})
