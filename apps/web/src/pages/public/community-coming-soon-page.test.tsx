import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen, within } from '@testing-library/react'
import { MemoryRouter } from 'react-router'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import App from '@/App'
import i18n from '@/i18n'
import { useAuthStore } from '@/stores/auth-store'
import { eventSliderRepository } from '@/features/events/repositories/event-slider-repository-provider'
import { publicEventsClient } from '@/features/events/public-event'

function renderPath(path: string) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false, gcTime: 0 } } })
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={[path]}>
        <App />
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

describe('public community Coming Soon routes', () => {
  beforeEach(async () => {
    vi.restoreAllMocks()
    await i18n.changeLanguage('en')
    useAuthStore.getState().clearSession()
    vi.spyOn(eventSliderRepository, 'listPublished').mockResolvedValue([])
  })

  it.each([
    ['en', '/events/recap', 'Previous Events Recap', 'Coming Soon', 'Back to Events'],
    ['en', '/merchandise', 'VGU Buddy Merchandise', 'Coming Soon', 'Back to Events'],
    [
      'de',
      '/events/recap',
      'Rückblicke auf vergangene Events',
      'Demnächst verfügbar',
      'Zurück zu den Events',
    ],
    ['de', '/merchandise', 'VGU Buddy Merchandise', 'Demnächst verfügbar', 'Zurück zu den Events'],
  ])(
    'loads %s direct %s without auth or Event detail requests',
    async (language, path, title, status, back) => {
      await i18n.changeLanguage(language)
      const readEvent = vi.spyOn(publicEventsClient, 'readEvent')
      renderPath(path)
      expect(screen.getByRole('heading', { level: 1, name: title })).toBeVisible()
      const main = screen.getByRole('main')
      expect(within(main).getByText(status)).toBeVisible()
      expect(within(main).getByRole('link', { name: back })).toHaveAttribute('href', '/#events')
      expect(main.querySelector('form, input, button')).toBeNull()
      expect(screen.getByRole('banner')).toBeVisible()
      expect(screen.getByRole('contentinfo')).toBeVisible()
      expect(readEvent).not.toHaveBeenCalled()
      expect(eventSliderRepository.listPublished).not.toHaveBeenCalled()
    },
  )

  it('navigates through both secondary cards and returns to the existing Events anchor', async () => {
    const originalScroll = HTMLElement.prototype.scrollIntoView
    const scroll = vi.fn()
    HTMLElement.prototype.scrollIntoView = scroll
    renderPath('/')
    const explore = screen.getByRole('region', { name: 'Explore More' })
    expect(
      within(explore)
        .getAllByRole('heading', { level: 3 })
        .map((h) => h.textContent),
    ).toEqual(['Previous Events Recap', 'Merchandise'])
    expect(
      within(explore)
        .getAllByRole('link')
        .map((a) => a.getAttribute('href')),
    ).toEqual(['/events/recap', '/merchandise'])
    for (const [action, title] of [
      ['Explore Recaps', 'Previous Events Recap'],
      ['Explore Merchandise', 'VGU Buddy Merchandise'],
    ]) {
      fireEvent.click(screen.getByRole('link', { name: action }))
      expect(screen.getByRole('heading', { level: 1, name: title })).toBeVisible()
      fireEvent.click(screen.getByRole('link', { name: 'Back to Events' }))
      expect(screen.getByRole('region', { name: 'Explore More' })).toBeVisible()
    }
    await vi.waitFor(() => expect(scroll).toHaveBeenCalled())
    HTMLElement.prototype.scrollIntoView = originalScroll
  })
})
