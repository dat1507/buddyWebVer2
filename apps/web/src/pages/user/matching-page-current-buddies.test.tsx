import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { act, cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { MemoryRouter } from 'react-router'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import type { CurrentBuddyList } from '@/features/matching/current-buddy'
import { matchingClient } from '@/features/matching/matching-client'
import { profileClient } from '@/features/profile/profile-client'
import i18n from '@/i18n'
import { ApiError } from '@/lib/api'
import { MatchingPage } from '@/pages/user/matching-page'
import { currentBuddyList } from '@/test/current-buddies'
import { incomingInvitationList, sentInvitationList } from '@/test/invitations'
import { completeProfileCompletion } from '@/test/profile-completion'
import { recommendationList } from '@/test/recommendations'

const emptyRecommendations = {
  ...recommendationList,
  items: [],
  total: 0,
  total_pages: 0,
}
const emptyIncoming = { ...incomingInvitationList, items: [], total: 0, total_pages: 0 }
const emptySent = { ...sentInvitationList, items: [], total: 0, total_pages: 0 }
const emptyBuddies = { ...currentBuddyList, items: [], total: 0, total_pages: 0 }

function deferred<T>() {
  let resolve!: (value: T) => void
  const promise = new Promise<T>((done) => {
    resolve = done
  })
  return { promise, resolve }
}

describe('BUDDY-003 Current Buddies section', () => {
  let client: QueryClient

  beforeEach(async () => {
    await i18n.changeLanguage('en')
    client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
    client.setQueryData(['profile', 'completion'], completeProfileCompletion)
    vi.spyOn(matchingClient, 'readRecommendations').mockResolvedValue(emptyRecommendations)
    vi.spyOn(matchingClient, 'readIncomingInvitations').mockResolvedValue(emptyIncoming)
    vi.spyOn(matchingClient, 'readSentInvitations').mockResolvedValue(emptySent)
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
    vi.restoreAllMocks()
  })

  const renderPage = (entry = '/user/matching') =>
    render(
      <QueryClientProvider client={client}>
        <MemoryRouter initialEntries={[entry]}>
          <MatchingPage />
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

  it('auto-loads a deep-linked later page and focuses only the exact conversation card', async () => {
    const second = {
      ...currentBuddyList.items[0],
      match_id: 'aaaaaaaa-4444-4444-8444-444444444444',
      conversation_id: 'bbbbbbbb-4444-4444-8444-444444444444',
      buddy: {
        ...currentBuddyList.items[0].buddy,
        id: 'cccccccc-4444-4444-8444-444444444444',
        display_name: 'Deep Link Buddy',
      },
    }
    vi.mocked(matchingClient.readCurrentBuddies)
      .mockResolvedValueOnce({ ...currentBuddyList, total: 21, total_pages: 2 })
      .mockResolvedValueOnce({
        ...currentBuddyList,
        page: 2,
        items: [second],
        total: 21,
        total_pages: 2,
      })
    renderPage(`/user/matching?conversation=${second.conversation_id}#current-buddies`)

    const focused = await screen.findByRole('article', { name: 'Deep Link Buddy' })
    await waitFor(() => expect(focused).toHaveFocus())
    expect(matchingClient.readCurrentBuddies).toHaveBeenCalledTimes(2)
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

  it('does not preload Buddy data while email verification is locked', () => {
    client.setQueryData(['profile', 'completion'], {
      ...completeProfileCompletion,
      matching_eligible: false,
      reasons: ['EMAIL_VERIFICATION_REQUIRED'],
    })
    renderPage()

    expect(screen.getByRole('heading', { name: 'Current Buddies are locked' })).toBeVisible()
    expect(
      within(screen.getByRole('region', { name: 'Current Buddies' })).getByRole('link', {
        name: 'Manage email verification',
      }),
    ).toHaveAttribute('href', '/user/settings')
    expect(matchingClient.readCurrentBuddies).not.toHaveBeenCalled()
  })

  it('keeps active Buddies available when new matching is opted out', async () => {
    client.setQueryData(['profile', 'completion'], {
      ...completeProfileCompletion,
      matching_eligible: false,
      reasons: ['MATCHING_OPT_IN_REQUIRED'],
    })
    vi.mocked(matchingClient.readCurrentBuddies).mockResolvedValueOnce(currentBuddyList)
    renderPage()

    expect(await screen.findByRole('article', { name: 'Linh' })).toBeVisible()
    expect(matchingClient.readCurrentBuddies).toHaveBeenCalledOnce()
    expect(matchingClient.readRecommendations).not.toHaveBeenCalled()
  })

  it('switches Current Buddies labels and requests localized safe profile labels in German', async () => {
    vi.mocked(matchingClient.readCurrentBuddies).mockResolvedValue(currentBuddyList)
    renderPage()
    await screen.findByRole('heading', { name: 'Current Buddies' })

    await act(async () => i18n.changeLanguage('de'))
    expect(await screen.findByRole('heading', { name: 'Aktuelle Buddys' })).toBeVisible()
    await waitFor(() =>
      expect(matchingClient.readCurrentBuddies).toHaveBeenCalledWith(
        expect.objectContaining({ locale: 'de', page: 1, pageSize: 20 }),
      ),
    )
  })
})
