import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { act, cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import type { InvitationCreateResponse } from '@/features/matching/invitation'
import { matchingClient } from '@/features/matching/matching-client'
import { profileClient } from '@/features/profile/profile-client'
import i18n from '@/i18n'
import { ApiError } from '@/lib/api'
import { MatchingPage } from '@/pages/user/matching-page'
import { incomingInvitationList, sentInvitationList } from '@/test/invitations'
import { completeProfileCompletion } from '@/test/profile-completion'
import { recommendationList } from '@/test/recommendations'

const emptyIncoming = {
  ...incomingInvitationList,
  items: [],
  total: 0,
  total_pages: 0,
}
const emptySent = {
  ...sentInvitationList,
  items: [],
  total: 0,
  total_pages: 0,
}

describe('INV-007 invitation UI', () => {
  let client: QueryClient

  beforeEach(async () => {
    await i18n.changeLanguage('en')
    client = new QueryClient({
      defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
    })
    client.setQueryData(['profile', 'completion'], completeProfileCompletion)
    vi.spyOn(matchingClient, 'readRecommendations').mockResolvedValue(recommendationList)
    vi.spyOn(matchingClient, 'readIncomingInvitations').mockResolvedValue(emptyIncoming)
    vi.spyOn(matchingClient, 'readSentInvitations').mockResolvedValue(emptySent)
    vi.spyOn(profileClient, 'readPhotoUrl').mockResolvedValue({
      id: recommendationList.items[0].profile.avatar.id,
      url: 'https://media.example.test/invitation-avatar',
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

  it('opens the accessible composer, submits exactly once, and reflects server-confirmed success', async () => {
    const receipt: InvitationCreateResponse = {
      id: 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa',
      status: 'PENDING',
      expires_at: '2026-10-08T08:00:00Z',
    }
    const sentAfterCreate = {
      ...sentInvitationList,
      items: [
        {
          ...sentInvitationList.items[0],
          id: receipt.id,
          recipient: recommendationList.items[0].profile,
        },
      ],
      total: 1,
    }
    let resolveSend!: (value: InvitationCreateResponse) => void
    const pendingSend = new Promise<InvitationCreateResponse>((resolve) => {
      resolveSend = resolve
    })
    const send = vi.spyOn(matchingClient, 'sendInvitation').mockReturnValue(pendingSend)
    vi.mocked(matchingClient.readSentInvitations)
      .mockResolvedValueOnce(emptySent)
      .mockResolvedValueOnce(sentAfterCreate)
      .mockResolvedValue(emptySent)
    const cancel = vi.spyOn(matchingClient, 'cancelInvitation').mockResolvedValue({
      invitation_id: receipt.id,
      status: 'CANCELLED',
    })
    renderPage()

    fireEvent.click(await screen.findByRole('button', { name: 'Send invitation' }))
    const dialog = screen.getByRole('dialog', { name: 'Invite Linh' })
    const message = screen.getByRole('textbox', { name: 'Invitation message' })
    expect(message).toHaveFocus()
    fireEvent.change(message, { target: { value: '  Hello   my\tfriend\n' } })
    expect(dialog).toHaveTextContent('3 / 500 words')
    expect(dialog).toHaveTextContent('17 / 10000 characters')

    const submit = screen.getByRole('button', { name: 'Send invitation' })
    fireEvent.click(submit)
    fireEvent.click(submit)
    await waitFor(() => expect(send).toHaveBeenCalledOnce())
    expect(send).toHaveBeenCalledWith({
      recipientProfileId: recommendationList.items[0].profile.id,
      message: 'Hello   my\tfriend',
    })
    expect(screen.getByRole('button', { name: 'Sending…' })).toBeDisabled()

    await act(async () => resolveSend(receipt))
    expect(await screen.findByText('Your invitation to Linh was sent.')).toBeVisible()
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Invitation sent' })).toBeDisabled()
    expect(matchingClient.readSentInvitations).toHaveBeenCalledTimes(2)

    fireEvent.click(screen.getByRole('button', { name: 'Cancel invitation' }))
    await waitFor(() => expect(cancel).toHaveBeenCalledWith(receipt.id))
    expect(await screen.findByRole('button', { name: 'Send invitation' })).toBeEnabled()
    expect(matchingClient.readSentInvitations).toHaveBeenCalledTimes(3)
  })

  it('enforces both shared message boundaries with Unicode code-point counting', async () => {
    renderPage()
    fireEvent.click(await screen.findByRole('button', { name: 'Send invitation' }))
    const message = screen.getByRole('textbox', { name: 'Invitation message' })

    fireEvent.change(message, { target: { value: Array(501).fill('w').join(' ') } })
    expect(screen.getByRole('alert')).toHaveTextContent('Use no more than 500 words.')
    expect(screen.getByRole('button', { name: 'Send invitation' })).toBeDisabled()

    fireEvent.change(message, { target: { value: '😀'.repeat(10_000) } })
    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
    expect(screen.getByText('10000 / 10000 characters')).toBeVisible()

    fireEvent.change(message, { target: { value: '😀'.repeat(10_001) } })
    expect(screen.getByRole('alert')).toHaveTextContent(
      'Use no more than 10,000 Unicode characters.',
    )
  })

  it('closes the composer with Escape and restores focus to its trigger', async () => {
    renderPage()
    const trigger = await screen.findByRole('button', { name: 'Send invitation' })
    trigger.focus()
    fireEvent.click(trigger)
    expect(screen.getByRole('textbox', { name: 'Invitation message' })).toHaveFocus()

    fireEvent.keyDown(document, { key: 'Escape' })
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
    expect(trigger).toHaveFocus()
  })

  it('renders incoming plain text inertly and accepts with a server-authoritative refresh', async () => {
    vi.mocked(matchingClient.readIncomingInvitations)
      .mockResolvedValueOnce(incomingInvitationList)
      .mockResolvedValue(emptyIncoming)
    const accept = vi.spyOn(matchingClient, 'acceptInvitation').mockResolvedValue({
      invitation_id: incomingInvitationList.items[0].id,
      status: 'ACCEPTED',
      match_id: 'bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb',
      conversation_id: 'cccccccc-cccc-4ccc-8ccc-cccccccccccc',
    })
    renderPage()

    expect(
      await screen.findByText((_, element) =>
        Boolean(
          element?.tagName === 'P' && element.textContent?.includes('<script>alert(1)</script>'),
        ),
      ),
    ).toBeVisible()
    expect(document.querySelector('script')).toBeNull()
    fireEvent.click(screen.getByRole('button', { name: 'Accept' }))
    await waitFor(() => expect(accept).toHaveBeenCalledOnce())
    expect(accept).toHaveBeenCalledWith(incomingInvitationList.items[0].id)
    expect(await screen.findByRole('heading', { name: 'No current invitations' })).toBeVisible()
  })

  it('declines an incoming invitation and removes it only after backend success', async () => {
    vi.mocked(matchingClient.readIncomingInvitations)
      .mockResolvedValueOnce(incomingInvitationList)
      .mockResolvedValue(emptyIncoming)
    const decline = vi.spyOn(matchingClient, 'declineInvitation').mockResolvedValue({
      invitation_id: incomingInvitationList.items[0].id,
      status: 'DECLINED',
    })
    renderPage()

    fireEvent.click(await screen.findByRole('button', { name: 'Decline' }))
    await waitFor(() => expect(decline).toHaveBeenCalledWith(incomingInvitationList.items[0].id))
    expect(await screen.findByRole('heading', { name: 'No current invitations' })).toBeVisible()
  })

  it('shows only Cancel for pending Sent rows and reconciles after cancellation', async () => {
    const pendingList = { ...sentInvitationList, items: [sentInvitationList.items[0]], total: 1 }
    vi.mocked(matchingClient.readSentInvitations)
      .mockResolvedValueOnce(pendingList)
      .mockResolvedValue(emptySent)
    const cancel = vi.spyOn(matchingClient, 'cancelInvitation').mockResolvedValue({
      invitation_id: sentInvitationList.items[0].id,
      status: 'CANCELLED',
    })
    renderPage()

    const cancelButton = await screen.findByRole('button', { name: 'Cancel invitation' })
    expect(screen.queryByRole('button', { name: 'Remove from Sent' })).not.toBeInTheDocument()
    fireEvent.click(cancelButton)
    await waitFor(() => expect(cancel).toHaveBeenCalledWith(sentInvitationList.items[0].id))
    expect(
      await screen.findByRole('heading', { name: 'No visible sent invitations' }),
    ).toBeVisible()
  })

  it('offers Start chatting and non-destructive hide only for accepted Sent rows', async () => {
    const accepted = sentInvitationList.items[1]
    const acceptedList = { ...sentInvitationList, items: [accepted], total: 1 }
    vi.mocked(matchingClient.readSentInvitations)
      .mockResolvedValueOnce(acceptedList)
      .mockResolvedValue(emptySent)
    const hide = vi.spyOn(matchingClient, 'hideInvitation').mockResolvedValue({
      invitation_id: accepted.id,
      status: 'ACCEPTED',
    })
    renderPage()

    expect(await screen.findByRole('link', { name: 'Start chatting' })).toHaveAttribute(
      'href',
      '/user/buddy',
    )
    expect(screen.getByText(/does not end your Buddy relationship/i)).toBeVisible()
    expect(screen.queryByRole('button', { name: 'Cancel invitation' })).not.toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Remove from Sent' }))
    await waitFor(() => expect(hide).toHaveBeenCalledWith(accepted.id))
    expect(
      await screen.findByRole('heading', { name: 'No visible sent invitations' }),
    ).toBeVisible()
  })

  it('maps a safe pending-limit reason and refetches stale matching state', async () => {
    const recommendationReadsBefore = vi.mocked(matchingClient.readRecommendations).mock.calls
      .length
    vi.spyOn(matchingClient, 'sendInvitation').mockRejectedValue(
      new ApiError(409, 'conflict', null, 'INVITATION_PENDING_LIMIT_REACHED'),
    )
    renderPage()
    fireEvent.click(await screen.findByRole('button', { name: 'Send invitation' }))
    fireEvent.click(screen.getByRole('button', { name: 'Send invitation' }))

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'You already have 30 pending invitations.',
    )
    expect(screen.queryByText('INVITATION_PENDING_LIMIT_REACHED')).not.toBeInTheDocument()
    await waitFor(() =>
      expect(matchingClient.readRecommendations).toHaveBeenCalledTimes(
        recommendationReadsBefore + 2,
      ),
    )
  })

  it('reconciles an invitation that expires while the page is open', async () => {
    vi.mocked(matchingClient.readIncomingInvitations)
      .mockResolvedValueOnce(incomingInvitationList)
      .mockResolvedValue(emptyIncoming)
    vi.spyOn(matchingClient, 'declineInvitation').mockRejectedValue(
      new ApiError(409, 'conflict', null, 'INVITATION_MUTATION_EXPIRED'),
    )
    renderPage()

    fireEvent.click(await screen.findByRole('button', { name: 'Decline' }))
    expect(await screen.findByRole('heading', { name: 'No current invitations' })).toBeVisible()
    expect(matchingClient.readIncomingInvitations).toHaveBeenCalledTimes(2)
  })

  it('loads the next server page without reordering or duplicating earlier rows', async () => {
    const firstPage = {
      ...incomingInvitationList,
      total: 21,
      total_pages: 2,
    }
    const secondPage = {
      ...incomingInvitationList,
      page: 2,
      total: 21,
      total_pages: 2,
      items: [
        incomingInvitationList.items[0],
        {
          ...incomingInvitationList.items[0],
          id: '44444444-aaaa-4444-8444-444444444444',
          sender: {
            ...incomingInvitationList.items[0].sender,
            id: '55555555-aaaa-4555-8555-555555555555',
            display_name: 'Minh',
          },
        },
      ],
    }
    vi.mocked(matchingClient.readIncomingInvitations)
      .mockResolvedValueOnce(firstPage)
      .mockResolvedValueOnce(secondPage)
    renderPage()

    await screen.findByRole('button', { name: 'Accept' })
    fireEvent.click(screen.getByRole('button', { name: 'Load more' }))
    expect(await screen.findByRole('heading', { name: 'Minh' })).toBeVisible()
    expect(screen.getAllByRole('button', { name: 'Accept' })).toHaveLength(2)
    expect(matchingClient.readIncomingInvitations).toHaveBeenNthCalledWith(2, {
      locale: 'en',
      page: 2,
      pageSize: 20,
      signal: expect.any(AbortSignal),
    })
  })

  it('restores invitations from a fresh server read after remount', async () => {
    vi.mocked(matchingClient.readIncomingInvitations).mockResolvedValue(incomingInvitationList)
    const first = renderPage()
    expect(await screen.findByRole('button', { name: 'Accept' })).toBeVisible()
    first.unmount()
    client.clear()
    client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
    client.setQueryData(['profile', 'completion'], completeProfileCompletion)

    renderPage()
    expect(await screen.findByRole('button', { name: 'Accept' })).toBeVisible()
    expect(matchingClient.readIncomingInvitations).toHaveBeenCalledTimes(2)
  })
})
