import '@/i18n'
import i18n from '@/i18n'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router'
import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import * as api from '@/features/recaps/recaps'
import { EventsExploreMore } from './events-explore-more'

vi.mock('@/config/launch-scope', () => ({ publicEventsEnabled: true }))
const photo = (index: number): api.RecapPhoto => ({
  id: `22222222-2222-4222-8222-${String(index).padStart(12, '0')}`,
  alt_en: `Campus memory ${index}`,
  alt_de: `Campus-Erinnerung ${index}`,
  caption_en: null,
  caption_de: null,
  width: 800,
  height: 600,
  sort_order: index,
})
const latest: api.Recap = {
  id: '11111111-1111-4111-8111-111111111111',
  related_event_id: null,
  title_en: 'Latest memory',
  title_de: 'Neueste Erinnerung',
  summary_en: null,
  summary_de: null,
  editorial_en: null,
  editorial_de: null,
  event_date: '2026-11-04',
  status: 'PUBLISHED',
  version: 1,
  thumbnail_id: photo(1).id,
  photos: [photo(0), photo(1)],
  cleanup_pending: false,
}
const listing: api.RecapList = {
  items: [latest, { ...latest, id: '33333333-3333-4333-8333-333333333333' }],
  mosaic: [],
  years: [2026],
  page: 1,
  total: 2,
  total_pages: 1,
  pending_cleanup: [],
}
beforeEach(() => {
  vi.spyOn(api, 'fetchRecaps').mockResolvedValue(listing)
  vi.spyOn(api, 'photoUrl').mockResolvedValue({
    url: 'https://media.example.test/thumbnail.webp',
    expires_in: 300,
  })
})
afterEach(async () => {
  vi.restoreAllMocks()
  await i18n.changeLanguage('en')
})
function mount(cached = false) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false, gcTime: 0 } } })
  if (cached) client.setQueryData(['recaps', 1, ''], listing)
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter>
        <EventsExploreMore />
      </MemoryRouter>
    </QueryClientProvider>,
  )
}
it.each(['en', 'de'])(
  'preserves both routes and honest Coming Soon state in %s',
  async (language) => {
    await i18n.changeLanguage(language)
    mount()
    expect(
      screen.getByRole('link', { name: i18n.t('eventsShowcase.recap.action') }),
    ).toHaveAttribute('href', '/events/recap')
    expect(
      screen.getByRole('link', { name: i18n.t('eventsShowcase.merchandise.action') }),
    ).toHaveAttribute('href', '/merchandise')
    expect(screen.getByText(i18n.t('features.merchPending'))).toBeVisible()
    expect(screen.queryByRole('button', { name: /buy|kaufen/i })).toBeNull()
    await screen.findByRole('img')
  },
)
it('uses the newest public Recap selected thumbnail via the existing signed-media API', async () => {
  mount()
  expect(await screen.findByRole('img', { name: 'Campus memory 1' })).toHaveAttribute(
    'loading',
    'lazy',
  )
  expect(api.fetchRecaps).toHaveBeenCalledWith(1, '', false, expect.any(AbortSignal))
  expect(api.photoUrl).toHaveBeenCalledWith(
    latest.id,
    photo(1).id,
    false,
    false,
    expect.any(AbortSignal),
  )
  expect(api.photoUrl).toHaveBeenCalledOnce()
})
it('reuses fresh gallery cache without another list request', async () => {
  mount(true)
  await screen.findByRole('img')
  expect(api.fetchRecaps).not.toHaveBeenCalled()
})
it('falls back to the first photo when no thumbnail is selected', async () => {
  vi.mocked(api.fetchRecaps).mockResolvedValue({
    ...listing,
    items: [{ ...latest, thumbnail_id: null }],
  })
  mount()
  await screen.findByRole('img', { name: 'Campus memory 0' })
  expect(api.photoUrl).toHaveBeenCalledWith(
    latest.id,
    photo(0).id,
    false,
    false,
    expect.any(AbortSignal),
  )
})
it.each(['empty', 'missing-photo', 'outage'])(
  'keeps an illustrated fallback and usable links for %s',
  async (state) => {
    if (state === 'outage')
      vi.mocked(api.fetchRecaps).mockRejectedValue(new Error('synthetic outage'))
    else
      vi.mocked(api.fetchRecaps).mockResolvedValue({
        ...listing,
        items: state === 'empty' ? [] : [{ ...latest, photos: [] }],
      })
    const { container } = mount()
    await waitFor(() => expect(api.fetchRecaps).toHaveBeenCalled())
    expect(container.querySelector('.explore-memory-art')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: i18n.t('eventsShowcase.recap.action') })).toBeVisible()
    expect(api.photoUrl).not.toHaveBeenCalled()
  },
)
it('replaces a broken thumbnail with artwork after the existing bounded retry', async () => {
  const { container } = mount()
  fireEvent.error(await screen.findByRole('img'))
  await waitFor(() => expect(api.photoUrl).toHaveBeenCalledTimes(2))
  fireEvent.error(await screen.findByRole('img'))
  expect(await screen.findByText(i18n.t('recaps.photoUnavailable'))).toBeInTheDocument()
  expect(container.querySelector('.explore-memory-art')).toBeInTheDocument()
  expect(screen.queryByRole('img')).toBeNull()
})
