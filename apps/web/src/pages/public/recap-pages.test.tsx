import '@/i18n'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router'
import i18n from '@/i18n'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
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
  afterEach(async () => {
    await i18n.changeLanguage('en')
  })
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
  it('shows all ten recent cards on one page and filters by year', async () => {
    const list = vi.spyOn(api, 'fetchRecaps').mockImplementation(async (page) => ({
      items: Array.from({ length: 10 }, (_, index) => ({
        ...record,
        id: `11111111-1111-4111-8111-1111111111${String(index).padStart(2, '0')}`,
      })),
      mosaic: [],
      years: [2026, 2025],
      page,
      total: 10,
      total_pages: 1,
      pending_cleanup: [],
    }))
    mount()
    await waitFor(() => expect(screen.getAllByRole('article')).toHaveLength(10))
    expect(screen.queryByRole('button', { name: 'Next' })).toBeNull()
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
  it.each([
    ['en', 'Explore More on Facebook'],
    ['de', 'Mehr auf Facebook entdecken'],
  ])('links to older memories safely in %s', async (language, label) => {
    await i18n.changeLanguage(language)
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
    const link = screen.getByRole('link', { name: label })
    expect(link).toHaveAttribute('href', 'https://www.facebook.com/VGUBuddyProgram')
    expect(link).toHaveAttribute('target', '_blank')
    expect(link).toHaveAttribute('rel', 'noopener noreferrer')
  })
})
