import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { act, cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { MemoryRouter } from 'react-router'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import type { CurrentBuddyList } from '@/features/matching/current-buddy'
import { matchingClient } from '@/features/matching/matching-client'
import { profileClient } from '@/features/profile/profile-client'
import i18n from '@/i18n'
import { ApiError } from '@/lib/api'
import { CurrentBuddyRoutePage } from '@/pages/user/current-buddy-route-page'
import { useAuthStore } from '@/stores/auth-store'
import { currentBuddyList } from '@/test/current-buddies'

const emptyBuddies = { ...currentBuddyList, items: [], total: 0, total_pages: 0 }
const verifiedUser = {
  id: 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa',
  email: 'student@example.com',
  role: 'USER' as const,
  email_verified: true,
  email_verified_at: '2026-10-01T08:00:00Z',
}

function deferred<T>() {
  let resolve!: (value: T) => void
  const promise = new Promise<T>((done) => {
    resolve = done
  })
  return { promise, resolve }
}

describe('BUDDY-003 Current Buddies in My Buddy', () => {
  let client: QueryClient

  beforeEach(async () => {
    await i18n.changeLanguage('en')
    client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
    useAuthStore.getState().setAuthenticated(verifiedUser)
    vi.spyOn(matchingClient, 'readCurrentBuddies').mockResolvedValue(emptyBuddies)
    vi.spyOn(profileClient, 'readPhotoUrl').mockResolvedValue({
      id: currentBuddyList.items[0].buddy.avatar!.id,
      url: 'https://media.example.test/current-buddy-avatar',
      expires_in: 300,
      expiresAt: Date.now() + 300_000,
    })
  })

  afterEach(() => {
    cleanup()
    client.clear()
    useAuthStore.getState().resetSession()
    vi.restoreAllMocks()
  })

  const renderPage = () =>
    render(
      <QueryClientProvider client={client}>
        <MemoryRouter initialEntries={['/user/buddy']}>
          <CurrentBuddyRoutePage />
        </MemoryRouter>
      </QueryClientProvider>,
    )

  it('separates initial loading from the successful zero-Buddy state', async () => {
    const pending = deferred<CurrentBuddyList>()
    vi.mocked(matchingClient.readCurrentBuddies).mockReturnValueOnce(pending.promise)
    renderPage()

    expect(screen.getByText('Loading your current Buddies…')).toBeVisible()
    await act(async () => pending.resolve(emptyBuddies))
    expect(await screen.findByRole('heading', { name: 'No current Buddies yet' })).toBeVisible()
    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
  })

  it('renders one privacy-safe Buddy card and navigates with the exact opaque conversation', async () => {
    vi.mocked(matchingClient.readCurrentBuddies).mockResolvedValueOnce(currentBuddyList)
    renderPage()

    expect(await screen.findByRole('heading', { level: 1, name: 'My Buddies' })).toBeVisible()
    const card = await screen.findByRole('article', { name: 'Linh' })
    expect(
      await within(card).findByRole('img', { name: 'Profile photo for Linh' }),
    ).toHaveAttribute('src', 'https://media.example.test/current-buddy-avatar')
    expect(within(card).getByText('Vietnamese student')).toBeVisible()
    expect(within(card).getByText('Computer Science')).toBeVisible()
    expect(within(card).getByText('Photography')).toBeVisible()
    expect(within(card).getByText('Formula 1')).toBeVisible()
    expect(within(card).getByText('English · Fluent')).toBeVisible()
    expect(within(card).getByText('Coffee chat')).toBeVisible()
    expect(within(card).getByText('Monday, 09:00–11:00')).toBeVisible()
    expect(within(card).getByText('75% match · 30 / 40 points')).toBeVisible()
    expect(within(card).getByText('Saved availability comparison week: Sep 21, 2026')).toBeVisible()
    expect(within(card).getAllByRole('progressbar')).toHaveLength(6)
    expect(within(card).getByRole('link', { name: 'Start chatting with Linh' })).toHaveAttribute(
      'href',
      `/user/buddy?conversation=${currentBuddyList.items[0].conversation_id}`,
    )
    expect(screen.queryByText(/private@example\.com/i)).not.toBeInTheDocument()
    expect(screen.queryByText(currentBuddyList.items[0].match_id)).not.toBeInTheDocument()
    expect(screen.queryByText(currentBuddyList.items[0].conversation_id)).not.toBeInTheDocument()
    expect(
      screen.queryByRole('button', { name: /unmatch|remove buddy|end buddy|delete match/i }),
    ).not.toBeInTheDocument()
  })

  it('renders many Buddy cards in server order without assuming a single relationship', async () => {
    const second = {
      ...currentBuddyList.items[0],
      match_id: 'aaaaaaaa-2222-4222-8222-222222222222',
      conversation_id: 'bbbbbbbb-2222-4222-8222-222222222222',
      buddy: {
        ...currentBuddyList.items[0].buddy,
        id: 'cccccccc-2222-4222-8222-222222222222',
        display_name: 'Alex with a display name that safely wraps on a narrow screen',
        avatar: null,
      },
    }
    vi.mocked(matchingClient.readCurrentBuddies).mockResolvedValueOnce({
      ...currentBuddyList,
      items: [currentBuddyList.items[0], second],
      total: 2,
    })
    renderPage()

    const cards = await screen.findAllByRole('article')
    expect(within(cards[0]).getByRole('heading', { name: 'Linh' })).toBeVisible()
    expect(
      within(cards[1]).getByRole('heading', {
        name: 'Alex with a display name that safely wraps on a narrow screen',
      }),
    ).toHaveClass('break-words')
    expect(
      within(cards[1]).getByRole('img', {
        name: 'Profile photo unavailable for Alex with a display name that safely wraps on a narrow screen',
      }),
    ).toBeVisible()
  })

  it('loads additional server pages, deduplicates defensively, and preserves page order', async () => {
    const second = {
      ...currentBuddyList.items[0],
      match_id: 'aaaaaaaa-3333-4333-8333-333333333333',
      conversation_id: 'bbbbbbbb-3333-4333-8333-333333333333',
      buddy: {
        ...currentBuddyList.items[0].buddy,
        id: 'cccccccc-3333-4333-8333-333333333333',
        display_name: 'Minh',
      },
    }
    const read = vi
      .mocked(matchingClient.readCurrentBuddies)
      .mockResolvedValueOnce({ ...currentBuddyList, total: 21, total_pages: 2 })
      .mockResolvedValueOnce({
        ...currentBuddyList,
        page: 2,
        items: [currentBuddyList.items[0], second],
        total: 21,
        total_pages: 2,
      })
    renderPage()
    await screen.findByRole('article', { name: 'Linh' })

    fireEvent.click(screen.getByRole('button', { name: 'Load more' }))
    expect(await screen.findByRole('article', { name: 'Minh' })).toBeVisible()
    expect(screen.getAllByRole('article')).toHaveLength(2)
    expect(read).toHaveBeenNthCalledWith(2, {
      locale: 'en',
      page: 2,
      pageSize: 20,
      signal: expect.any(AbortSignal),
    })
    expect(
      screen.getByText('You have reached the end of your current Buddy relationships.'),
    ).toBeVisible()
  })

  it('keeps API failure separate, sanitized and retryable', async () => {
    vi.mocked(matchingClient.readCurrentBuddies)
      .mockRejectedValueOnce(new ApiError(503, 'server'))
      .mockResolvedValueOnce(currentBuddyList)
    renderPage()

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'We could not load your current Buddy relationships.',
    )
    expect(screen.queryByText(/API request failed|503|server/i)).not.toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Try again' }))
    expect(await screen.findByRole('article', { name: 'Linh' })).toBeVisible()
  })

  it('keeps My Buddy visible but locked while email verification is missing', () => {
    useAuthStore.getState().setAuthenticated({
      ...verifiedUser,
      email_verified: false,
      email_verified_at: null,
    })
    renderPage()

    expect(screen.getByRole('heading', { level: 1, name: 'My Buddies' })).toBeVisible()
    expect(screen.getByRole('heading', { name: 'Current Buddies are locked' })).toBeVisible()
    expect(
      within(screen.getByRole('region', { name: 'Current Buddies' })).getByRole('link', {
        name: 'Manage email verification',
      }),
    ).toHaveAttribute('href', '/user/settings')
    expect(matchingClient.readCurrentBuddies).not.toHaveBeenCalled()
  })

  it('switches Current Buddies labels and requests localized safe profile labels in German', async () => {
    vi.mocked(matchingClient.readCurrentBuddies).mockResolvedValue(currentBuddyList)
    renderPage()
    await screen.findByRole('heading', { name: 'Current Buddies' })

    await act(async () => i18n.changeLanguage('de'))
    expect(await screen.findByRole('heading', { level: 1, name: 'Meine Buddys' })).toBeVisible()
    expect(screen.getByRole('heading', { name: 'Aktuelle Buddys' })).toBeVisible()
    await waitFor(() =>
      expect(matchingClient.readCurrentBuddies).toHaveBeenCalledWith(
        expect.objectContaining({ locale: 'de', page: 1, pageSize: 20 }),
      ),
    )
  })
})
