import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { MemoryRouter } from 'react-router'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { matchingClient } from '@/features/matching/matching-client'
import { profileClient } from '@/features/profile/profile-client'
import i18n from '@/i18n'
import { ApiError } from '@/lib/api'
import { MatchingPage } from '@/pages/user/matching-page'
import { completeProfileCompletion } from '@/test/profile-completion'
import { recommendationList } from '@/test/recommendations'

describe('REC-004 Recommended Buddies page', () => {
  let client: QueryClient

  beforeEach(async () => {
    await i18n.changeLanguage('en')
    client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
    client.setQueryData(['profile', 'completion'], completeProfileCompletion)
    vi.spyOn(profileClient, 'readPhotoUrl').mockResolvedValue({
      id: recommendationList.items[0].profile.avatar.id,
      url: 'https://media.example.test/recommendation-avatar',
      expires_in: 300,
      expiresAt: Date.now() + 300_000,
    })
  })

  afterEach(() => {
    cleanup()
    client.clear()
    vi.restoreAllMocks()
  })

  const renderPage = () =>
    render(
      <QueryClientProvider client={client}>
        <MemoryRouter>
          <MatchingPage />
        </MemoryRouter>
      </QueryClientProvider>,
    )

  it('renders safe profile, preference, compatibility and availability data without invitation UI', async () => {
    const read = vi
      .spyOn(matchingClient, 'readRecommendations')
      .mockResolvedValue(recommendationList)
    renderPage()

    expect(screen.getByRole('status')).toHaveTextContent('Loading your recommendations')
    const card = await screen.findByRole('article', { name: 'Linh' })
    expect(
      await within(card).findByRole('img', { name: 'Profile photo for Linh' }),
    ).toHaveAttribute('src', 'https://media.example.test/recommendation-avatar')
    expect(within(card).getByText('Vietnamese student')).toBeVisible()
    expect(within(card).getByText('Computer Science')).toBeVisible()
    expect(within(card).getByText('87%')).toBeVisible()
    expect(within(card).getByText('Photography')).toBeVisible()
    expect(within(card).getByText('Formula 1')).toBeVisible()
    expect(within(card).getByText('English · Fluent')).toBeVisible()
    expect(within(card).getByText('Thai · Beginner')).toBeVisible()
    expect(within(card).getByText('Monday, 09:00–11:00')).toBeVisible()
    expect(within(card).getByText('75% match · 30 / 40 points')).toBeVisible()
    expect(within(card).getAllByRole('progressbar')).toHaveLength(6)
    expect(screen.getByText('Availability comparison week: Sep 21, 2026')).toBeVisible()
    expect(screen.queryByRole('button', { name: /send invitation/i })).not.toBeInTheDocument()
    expect(screen.queryByText(/invitation/i)).not.toBeInTheDocument()
    expect(read).toHaveBeenCalledWith({
      locale: 'en',
      page: 1,
      pageSize: 20,
      signal: expect.any(AbortSignal),
    })
  })

  it('does not preload recommendation or avatar data while matching is locked', () => {
    client.setQueryData(['profile', 'completion'], {
      ...completeProfileCompletion,
      matching_eligible: false,
      reasons: ['EMAIL_VERIFICATION_REQUIRED'],
    })
    const read = vi.spyOn(matchingClient, 'readRecommendations')
    renderPage()

    expect(screen.getByRole('heading', { name: 'Recommendations are locked' })).toBeVisible()
    expect(screen.getByRole('link', { name: 'Manage email verification' })).toHaveAttribute(
      'href',
      '/user/settings',
    )
    expect(read).not.toHaveBeenCalled()
    expect(profileClient.readPhotoUrl).not.toHaveBeenCalled()
  })

  it('keeps long custom labels contained and falls back safely when an avatar cannot load', async () => {
    const longLabel =
      'A custom interest label that remains readable without overflowing the recommendation card'
    vi.mocked(profileClient.readPhotoUrl).mockRejectedValueOnce(new ApiError(503, 'server'))
    vi.spyOn(matchingClient, 'readRecommendations').mockResolvedValue({
      ...recommendationList,
      items: [
        {
          ...recommendationList.items[0],
          profile: {
            ...recommendationList.items[0].profile,
            interests: [
              ...recommendationList.items[0].profile.interests,
              { id: null, code: null, label: longLabel, is_custom: true },
            ],
          },
        },
      ],
    })
    renderPage()

    expect(
      await screen.findByRole('img', { name: 'Profile photo unavailable for Linh' }),
    ).toBeVisible()
    expect(screen.getByText(longLabel).closest('li')).toHaveClass('max-w-full', 'break-words')
  })

  it('renders multiple candidates in exactly the order returned by the server', async () => {
    const second = {
      ...recommendationList.items[0],
      score: 99,
      profile: {
        ...recommendationList.items[0].profile,
        id: '66666666-6666-4666-8666-666666666666',
        display_name: 'Alex',
      },
    }
    vi.spyOn(matchingClient, 'readRecommendations').mockResolvedValue({
      ...recommendationList,
      items: [recommendationList.items[0], second],
      total: 2,
    })
    renderPage()

    const cards = await screen.findAllByRole('article')
    expect(cards.map((card) => card.getAttribute('aria-labelledby'))).toHaveLength(2)
    expect(within(cards[0]).getByRole('heading', { name: 'Linh' })).toBeVisible()
    expect(within(cards[1]).getByRole('heading', { name: 'Alex' })).toBeVisible()
    expect(screen.queryByText(/private@example\.com/i)).not.toBeInTheDocument()
    expect(screen.queryByText(recommendationList.items[0].profile.id)).not.toBeInTheDocument()
  })

  it('renders empty and sanitized retryable error states', async () => {
    const read = vi
      .spyOn(matchingClient, 'readRecommendations')
      .mockResolvedValueOnce({ ...recommendationList, items: [], total: 0, total_pages: 0 })
    const first = renderPage()
    expect(await screen.findByRole('heading', { name: 'No recommendations yet' })).toBeVisible()
    first.unmount()
    client.clear()
    client.setQueryData(['profile', 'completion'], completeProfileCompletion)

    read
      .mockRejectedValueOnce(new ApiError(503, 'server'))
      .mockResolvedValueOnce(recommendationList)
    renderPage()
    expect(await screen.findByRole('alert')).toHaveTextContent(
      'We could not load your current recommendations.',
    )
    expect(screen.queryByText('API request failed')).not.toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Try again' }))
    expect(await screen.findByRole('article', { name: 'Linh' })).toBeVisible()
  })

  it('requests the next server page and keeps the server-provided order', async () => {
    const firstPage = {
      ...recommendationList,
      total: 21,
      total_pages: 2,
    }
    const secondPage = {
      ...recommendationList,
      page: 2,
      total: 21,
      total_pages: 2,
      items: [
        {
          ...recommendationList.items[0],
          profile: {
            ...recommendationList.items[0].profile,
            id: '55555555-5555-4555-8555-555555555555',
            display_name: 'Minh',
          },
        },
      ],
    }
    const read = vi
      .spyOn(matchingClient, 'readRecommendations')
      .mockResolvedValueOnce(firstPage)
      .mockResolvedValueOnce(secondPage)
    renderPage()
    await screen.findByRole('article', { name: 'Linh' })

    fireEvent.click(screen.getByRole('button', { name: 'Next' }))
    expect(await screen.findByRole('article', { name: 'Minh' })).toBeVisible()
    await waitFor(() => expect(read).toHaveBeenCalledTimes(2))
    expect(read.mock.calls[1][0]).toEqual({
      locale: 'en',
      page: 2,
      pageSize: 20,
      signal: expect.any(AbortSignal),
    })
    expect(screen.getByText('Page 2 of 2')).toBeVisible()
    expect(screen.getByRole('button', { name: 'Next' })).toBeDisabled()
  })

  it('switches labels and re-queries localized recommendations in German', async () => {
    const read = vi
      .spyOn(matchingClient, 'readRecommendations')
      .mockResolvedValue(recommendationList)
    renderPage()
    await screen.findByRole('article', { name: 'Linh' })

    await i18n.changeLanguage('de')
    expect(
      await screen.findByRole('heading', { level: 1, name: 'Empfohlene Buddys' }),
    ).toBeVisible()
    await waitFor(() =>
      expect(read).toHaveBeenCalledWith(
        expect.objectContaining({ locale: 'de', page: 1, pageSize: 20 }),
      ),
    )
  })
})
