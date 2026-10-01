import { afterEach, describe, expect, it, vi } from 'vitest'

import { sessionClient } from '@/features/auth/session-client'
import { matchingClient } from '@/features/matching/matching-client'
import { currentBuddyList } from '@/test/current-buddies'
import { incomingInvitationList, sentInvitationList } from '@/test/invitations'
import { recommendationList } from '@/test/recommendations'

describe('REC-004 / INV-007 / BUDDY-003 matching client', () => {
  afterEach(() => vi.restoreAllMocks())

  it('calls only the read-only recommendation endpoint with bounded paging and locale', async () => {
    const authenticatedJson = vi
      .spyOn(sessionClient, 'authenticatedJson')
      .mockResolvedValue(recommendationList)
    const controller = new AbortController()

    await expect(
      matchingClient.readRecommendations({
        locale: 'de',
        page: 2,
        pageSize: 20,
        signal: controller.signal,
      }),
    ).resolves.toEqual(recommendationList)

    expect(authenticatedJson).toHaveBeenCalledWith(
      '/matching/recommendations?locale=de&page=2&page_size=20',
      { signal: controller.signal },
    )
    expect(authenticatedJson.mock.calls[0][1]).not.toHaveProperty('method')
  })

  it('reads the owner Current Buddies page without a mutation or client-side identity input', async () => {
    const authenticatedJson = vi
      .spyOn(sessionClient, 'authenticatedJson')
      .mockResolvedValue(currentBuddyList)
    const controller = new AbortController()

    await expect(
      matchingClient.readCurrentBuddies({
        locale: 'de',
        page: 2,
        pageSize: 20,
        signal: controller.signal,
      }),
    ).resolves.toEqual(currentBuddyList)
    expect(authenticatedJson).toHaveBeenCalledWith(
      '/matching/buddies?locale=de&page=2&page_size=20',
      { signal: controller.signal },
    )
    expect(authenticatedJson.mock.calls[0][1]).not.toHaveProperty('method')
  })

  it('reads owner invitation pages using bounded server pagination and locale', async () => {
    const authenticatedJson = vi
      .spyOn(sessionClient, 'authenticatedJson')
      .mockResolvedValueOnce(incomingInvitationList)
      .mockResolvedValueOnce(sentInvitationList)

    await expect(
      matchingClient.readIncomingInvitations({ locale: 'en', page: 1, pageSize: 20 }),
    ).resolves.toEqual(incomingInvitationList)
    await expect(
      matchingClient.readSentInvitations({ locale: 'de', page: 2, pageSize: 20 }),
    ).resolves.toEqual(sentInvitationList)

    expect(authenticatedJson).toHaveBeenNthCalledWith(
      1,
      '/matching/invitations/incoming?locale=en&page=1&page_size=20',
      { signal: undefined },
    )
    expect(authenticatedJson).toHaveBeenNthCalledWith(
      2,
      '/matching/invitations/sent?locale=de&page=2&page_size=20',
      { signal: undefined },
    )
  })

  it('sends one canonical invitation payload and validates the receipt', async () => {
    const response = {
      id: 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa',
      status: 'PENDING',
      expires_at: '2026-10-08T08:00:00Z',
    }
    const authenticatedJson = vi
      .spyOn(sessionClient, 'authenticatedJson')
      .mockResolvedValue(response)

    await expect(
      matchingClient.sendInvitation({
        recipientProfileId: 'bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb',
        message: 'Hello friend',
      }),
    ).resolves.toEqual(response)
    expect(authenticatedJson).toHaveBeenCalledOnce()
    expect(authenticatedJson).toHaveBeenCalledWith('/matching/invitations', {
      method: 'POST',
      body: {
        recipient_profile_id: 'bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb',
        message: 'Hello friend',
      },
    })
  })

  it.each([
    ['acceptInvitation', 'accept', 'ACCEPTED'],
    ['declineInvitation', 'decline', 'DECLINED'],
    ['cancelInvitation', 'cancel', 'CANCELLED'],
    ['hideInvitation', 'hide', 'ACCEPTED'],
  ] as const)('calls the exact %s endpoint contract', async (method, action, status) => {
    const invitationId = 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa'
    const response =
      action === 'accept'
        ? {
            invitation_id: invitationId,
            status,
            match_id: 'bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb',
            conversation_id: 'cccccccc-cccc-4ccc-8ccc-cccccccccccc',
          }
        : { invitation_id: invitationId, status }
    const authenticatedJson = vi
      .spyOn(sessionClient, 'authenticatedJson')
      .mockResolvedValue(response)

    await expect(matchingClient[method](invitationId)).resolves.toEqual(response)
    expect(authenticatedJson).toHaveBeenCalledWith(
      `/matching/invitations/${invitationId}/${action}`,
      { method: 'POST' },
    )
  })
})
