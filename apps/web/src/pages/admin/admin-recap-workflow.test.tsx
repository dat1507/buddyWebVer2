import '@/i18n'
import i18n from '@/i18n'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { MemoryRouter, Routes, Route } from 'react-router'
import { afterEach, it, expect, vi } from 'vitest'
import * as recaps from '@/features/recaps/recaps'
import { adminEventsClient } from '@/features/admin-events/admin-events'
import { AdminRecapEditorPage } from './admin-recap-pages'
vi.mock('@/features/recaps/recap-photo', () => ({
  RecapImage: () => <img alt="Synthetic photo" />,
}))
const record: recaps.Recap = {
  id: '11111111-1111-4111-8111-111111111111',
  related_event_id: null,
  title_en: 'New memory',
  title_de: 'Neue Erinnerung',
  summary_en: 'Day',
  summary_de: 'Tag',
  editorial_en: null,
  editorial_de: null,
  event_date: null,
  status: 'DRAFT',
  version: 1,
  thumbnail_id: null,
  photos: [],
  cleanup_pending: false,
}
afterEach(async () => {
  vi.restoreAllMocks()
  await i18n.changeLanguage('en')
})
it.each(['en', 'de'])(
  'publishes without another confirmation and announces permanent overflow deletion in %s',
  async (lang) => {
    await i18n.changeLanguage(lang)
    vi.spyOn(recaps, 'fetchRecap').mockResolvedValue(record)
    vi.spyOn(adminEventsClient, 'readEvents').mockResolvedValue({
      items: [],
      page: 1,
      page_size: 20,
      total: 0,
      total_pages: 0,
    })
    const mutate = vi.spyOn(recaps, 'mutateRecap').mockImplementation(async (path) =>
      path.endsWith('/status')
        ? {
            ...record,
            status: 'PUBLISHED',
            version: 3,
            evicted_recaps: [
              {
                id: '22222222-2222-4222-8222-222222222222',
                title_en: 'Old memory',
                title_de: 'Alte Erinnerung',
              },
            ],
          }
        : { ...record, version: 2 },
    )
    const client = new QueryClient({ defaultOptions: { queries: { retry: false, gcTime: 0 } } })
    render(
      <QueryClientProvider client={client}>
        <MemoryRouter initialEntries={['/admin/events/recaps/' + record.id + '/edit']}>
          <Routes>
            <Route path="/admin/events/recaps/:recapId/edit" element={<AdminRecapEditorPage />} />
          </Routes>
        </MemoryRouter>
      </QueryClientProvider>,
    )
    const button = await screen.findByRole('button', { name: i18n.t('recaps.publish') })
    fireEvent.click(button)
    await waitFor(() =>
      expect(mutate).toHaveBeenCalledWith('/' + record.id + '/status', 'PATCH', {
        version: 2,
        status: 'PUBLISHED',
      }),
    )
    expect(await screen.findByText(lang === 'de' ? /Alte Erinnerung/ : /Old memory/)).toBeVisible()
    expect(screen.queryByRole('dialog')).toBeNull()
    client.clear()
  },
)
