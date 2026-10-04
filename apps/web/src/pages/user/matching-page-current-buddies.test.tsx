import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { cleanup, render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { matchingClient } from '@/features/matching/matching-client'
import i18n from '@/i18n'
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

describe('Buddy Matching presentation', () => {
  let client: QueryClient

  beforeEach(async () => {
    await i18n.changeLanguage('en')
    client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
    client.setQueryData(['profile', 'completion'], completeProfileCompletion)
    vi.spyOn(matchingClient, 'readRecommendations').mockResolvedValue(emptyRecommendations)
    vi.spyOn(matchingClient, 'readIncomingInvitations').mockResolvedValue(emptyIncoming)
    vi.spyOn(matchingClient, 'readSentInvitations').mockResolvedValue(emptySent)
    vi.spyOn(matchingClient, 'readCurrentBuddies').mockResolvedValue(currentBuddyList)
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

  it('does not render or fetch Current Buddies on Buddy Matching', async () => {
    renderPage()

    expect(await screen.findByRole('heading', { name: 'Recommendation results' })).toBeVisible()
    expect(screen.queryByRole('heading', { name: 'Current Buddies' })).not.toBeInTheDocument()
    expect(screen.queryByRole('article', { name: 'Linh' })).not.toBeInTheDocument()
    expect(matchingClient.readCurrentBuddies).not.toHaveBeenCalled()
  })

  it('does not restore Current Buddies from the former matching-page conversation locator', async () => {
    renderPage(
      `/user/matching?conversation=${currentBuddyList.items[0].conversation_id}#current-buddies`,
    )

    expect(await screen.findByRole('heading', { name: 'Invitations' })).toBeVisible()
    expect(screen.queryByRole('heading', { name: 'Current Buddies' })).not.toBeInTheDocument()
    expect(matchingClient.readCurrentBuddies).not.toHaveBeenCalled()
  })
})
