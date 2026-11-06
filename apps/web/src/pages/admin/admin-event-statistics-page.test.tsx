import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, cleanup } from '@testing-library/react'
import { MemoryRouter } from 'react-router'
import { afterEach, it, expect, vi } from 'vitest'
import { AdminEventStatisticsPage } from './admin-event-statistics-page'
import { useAuthStore } from '@/stores/auth-store'
import i18n from '@/i18n'
afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
  vi.unstubAllEnvs()
  useAuthStore.getState().resetSession()
})
it.each(['en', 'de'])('shows real aggregate cards and three tabs in %s', async (language) => {
  await i18n.changeLanguage(language)
  vi.stubEnv('VITE_API_URL', '/api')
  useAuthStore.getState().setAuthenticated({
    id: 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa',
    email: 'admin@example.com',
    role: 'ADMIN',
    email_verified: true,
  })
  const fetch = vi.fn().mockResolvedValue(
    new Response(
      JSON.stringify({
        published_events: 12,
        upcoming_events: 0,
        observed_at: '2026-11-06T00:00:00Z',
      }),
    ),
  )
  vi.stubGlobal('fetch', fetch)
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={['/admin/events/statistics']}>
        <AdminEventStatisticsPage />
      </MemoryRouter>
    </QueryClientProvider>,
  )
  expect(await screen.findByText('12')).toBeVisible()
  expect(screen.getByText('0')).toBeVisible()
  expect(screen.getAllByRole('link')).toHaveLength(3)
  expect(
    screen.getByRole('link', { name: language === 'en' ? 'Statistics' : 'Statistik' }),
  ).toHaveAttribute('aria-current', 'page')
  expect(
    screen.getByRole('button', { name: language === 'en' ? 'Refresh' : 'Aktualisieren' }),
  ).toBeEnabled()
  client.clear()
})
