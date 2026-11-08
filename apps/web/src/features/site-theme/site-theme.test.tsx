import { QueryClientProvider, focusManager } from '@tanstack/react-query'
import { act, cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { MemoryRouter } from 'react-router'
import { afterEach, beforeEach, expect, it, vi } from 'vitest'

import { SiteThemeBoundary } from '@/features/site-theme/site-theme-boundary'
import {
  parseThemeId,
  siteThemeClient,
  themeIds,
  useSiteTheme,
} from '@/features/site-theme/site-theme'
import i18n from '@/i18n'
import { queryClient } from '@/lib/query-client'
import { AdminSettingsPage } from '@/pages/admin/admin-settings-page'
import { useAuthStore } from '@/stores/auth-store'

function ThemedPage() {
  return <main data-site-theme={useSiteTheme()}>Student page</main>
}

beforeEach(async () => {
  await i18n.changeLanguage('en')
  queryClient.clear()
})

afterEach(() => {
  cleanup()
  focusManager.setFocused(undefined)
  queryClient.clear()
  useAuthStore.getState().resetSession()
  vi.restoreAllMocks()
})

it('allows only the four approved presets', () => {
  expect(themeIds).toEqual(['default', 'halloween', 'christmas', 'summer'])
  for (const theme of themeIds) expect(parseThemeId(theme)).toBe(theme)
  expect(parseThemeId('purple')).toBeUndefined()
})

it('applies the published theme, revalidates on focus and falls back on failure', async () => {
  const read = vi
    .spyOn(siteThemeClient, 'read')
    .mockResolvedValueOnce('halloween')
    .mockResolvedValueOnce('christmas')
    .mockRejectedValueOnce(new Error('offline'))
  render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <SiteThemeBoundary>
          <ThemedPage />
        </SiteThemeBoundary>
        <aside>Admin outside the theme</aside>
      </MemoryRouter>
    </QueryClientProvider>,
  )
  const main = screen.getByRole('main')
  await waitFor(() => expect(main).toHaveAttribute('data-site-theme', 'halloween'))
  expect(screen.getByRole('complementary')).not.toHaveAttribute('data-site-theme')
  await act(async () => {
    focusManager.setFocused(false)
    focusManager.setFocused(true)
  })
  await waitFor(() => expect(main).toHaveAttribute('data-site-theme', 'christmas'))
  await act(async () => {
    focusManager.setFocused(false)
    focusManager.setFocused(true)
  })
  await waitFor(() => expect(main).not.toHaveAttribute('data-site-theme'))
  expect(read).toHaveBeenCalledTimes(3)
})

it('polls after one minute and stops when the user-side layout unmounts', async () => {
  vi.useFakeTimers()
  try {
    focusManager.setFocused(true)
    const read = vi.spyOn(siteThemeClient, 'read').mockResolvedValue('summer')
    const view = render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter>
          <SiteThemeBoundary>
            <ThemedPage />
          </SiteThemeBoundary>
        </MemoryRouter>
      </QueryClientProvider>,
    )
    await act(async () => {
      await vi.advanceTimersByTimeAsync(10)
    })
    expect(screen.getByRole('main')).toHaveAttribute('data-site-theme', 'summer')
    const first = read.mock.calls.length
    await act(async () => {
      await vi.advanceTimersByTimeAsync(60_010)
    })
    expect(read).toHaveBeenCalledTimes(first + 1)
    view.unmount()
    await vi.advanceTimersByTimeAsync(60_010)
    expect(read).toHaveBeenCalledTimes(first + 1)
  } finally {
    vi.useRealTimers()
  }
})

it('uses a localhost preview without reading or publishing the live theme', async () => {
  vi.stubEnv('VITE_SEASONAL_PREVIEW', 'true')
  const read = vi.spyOn(siteThemeClient, 'read').mockResolvedValue('summer')
  const publish = vi.spyOn(siteThemeClient, 'publish')
  try {
    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter initialEntries={['/?theme-preview=christmas']}>
          <SiteThemeBoundary>
            <ThemedPage />
          </SiteThemeBoundary>
        </MemoryRouter>
      </QueryClientProvider>,
    )
    expect(screen.getByRole('main')).toHaveAttribute('data-site-theme', 'christmas')
    expect(read).not.toHaveBeenCalled()
    expect(publish).not.toHaveBeenCalled()
  } finally {
    window.sessionStorage.removeItem('buddyweb-local-theme-preview')
    vi.unstubAllEnvs()
  }
})

function openSettings() {
  useAuthStore.getState().setAuthenticated({
    id: 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa',
    role: 'ADMIN',
    email: 'admin@example.invalid',
    email_verified: false,
    email_verified_at: null,
  })
  render(
    <QueryClientProvider client={queryClient}>
      <AdminSettingsPage />
    </QueryClientProvider>,
  )
}

it('previews without writing, confirms publication and allows restoring Default', async () => {
  vi.spyOn(siteThemeClient, 'readAdmin').mockResolvedValue('default')
  const publish = vi
    .spyOn(siteThemeClient, 'publish')
    .mockResolvedValueOnce('summer')
    .mockResolvedValueOnce('default')
  openSettings()
  const presets = screen.getByRole('group', { name: 'Theme presets' })
  await screen.findByText('Currently published: Default.')
  expect(screen.getByRole('button', { name: 'Publish theme' })).toBeDisabled()
  fireEvent.click(within(presets).getByRole('button', { name: /Summer/ }))
  fireEvent.click(screen.getByRole('button', { name: 'User Dashboard' }))
  expect(screen.getByText('Your Buddy journey').closest('[data-theme-sample]')).toHaveAttribute(
    'data-theme-sample',
    'summer',
  )
  expect(document.querySelector('[data-seasonal-scene=summer]')).toHaveAttribute(
    'data-scene-placement',
    'sample',
  )
  expect(document.querySelector('[data-site-theme]')).toBeNull()
  expect(publish).not.toHaveBeenCalled()
  for (const preset of ['summer', 'default']) {
    if (preset === 'default')
      fireEvent.click(within(presets).getByRole('button', { name: /Default/ }))
    fireEvent.click(screen.getByRole('button', { name: 'Publish theme' }))
    const dialog = screen.getByRole('alertdialog')
    fireEvent.click(within(dialog).getByRole('button', { name: 'Publish theme' }))
    await waitFor(() => expect(dialog).not.toBeInTheDocument())
    expect(publish).toHaveBeenLastCalledWith(preset, expect.anything())
  }
  expect(screen.getByText('Currently published: Default.')).toBeVisible()
})

it('keeps publishing disabled during a load error and offers retry', async () => {
  vi.spyOn(siteThemeClient, 'readAdmin')
    .mockRejectedValueOnce(new Error('offline'))
    .mockResolvedValue('halloween')
  queryClient.setDefaultOptions({ queries: { retry: false } })
  try {
    openSettings()
    expect(screen.getByRole('button', { name: 'Publish theme' })).toBeDisabled()
    await screen.findByRole('alert')
    fireEvent.click(screen.getByRole('button', { name: 'Try again' }))
    expect(await screen.findByText('Currently published: Halloween.')).toBeVisible()
  } finally {
    queryClient.setDefaultOptions({
      queries: { retry: 1, staleTime: 30_000, refetchOnWindowFocus: true },
    })
  }
})
