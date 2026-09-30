import { sessionClient } from '@/features/auth/session-client'
import {
  incomingInvitationListSchema,
  invitationAcceptResponseSchema,
  invitationCreateResponseSchema,
  invitationMutationResponseSchema,
  parseContract,
  sentInvitationListSchema,
} from '@/features/matching/invitation'
import type {
  IncomingInvitationList,
  InvitationAcceptResponse,
  InvitationCreateResponse,
  InvitationMutationResponse,
  SentInvitationList,
} from '@/features/matching/invitation'
import {
  parseRecommendationList,
  type RecommendationList,
} from '@/features/matching/recommendation'
import type { CatalogLocale } from '@/features/profile/profile-catalog'
import { ApiError } from '@/lib/api'

interface RecommendationRequest {
  locale: CatalogLocale
  page: number
  pageSize: number
  signal?: AbortSignal
}

type InvitationListRequest = RecommendationRequest

interface SendInvitationRequest {
  recipientProfileId: string
  message: string
}

type InvitationMutationStatus = InvitationMutationResponse['status']

function invitationListPath(view: 'incoming' | 'sent', request: InvitationListRequest): string {
  const search = new URLSearchParams({
    locale: request.locale,
    page: String(request.page),
    page_size: String(request.pageSize),
  })
  return `/matching/invitations/${view}?${search}`
}

async function mutateInvitation(
  invitationId: string,
  action: 'decline' | 'cancel' | 'hide',
  expectedStatus: InvitationMutationStatus,
): Promise<InvitationMutationResponse> {
  const result = parseContract(
    invitationMutationResponseSchema,
    await sessionClient.authenticatedJson(`/matching/invitations/${invitationId}/${action}`, {
      method: 'POST',
    }),
  )
  if (result.invitation_id !== invitationId || result.status !== expectedStatus) {
    throw new ApiError(200, 'invalidResponse')
  }
  return result
}

const matchingClient = {
  async readRecommendations({
    locale,
    page,
    pageSize,
    signal,
  }: RecommendationRequest): Promise<RecommendationList> {
    const search = new URLSearchParams({
      locale,
      page: String(page),
      page_size: String(pageSize),
    })
    return parseRecommendationList(
      await sessionClient.authenticatedJson(`/matching/recommendations?${search}`, { signal }),
    )
  },
  async readIncomingInvitations(request: InvitationListRequest): Promise<IncomingInvitationList> {
    return parseContract(
      incomingInvitationListSchema,
      await sessionClient.authenticatedJson(invitationListPath('incoming', request), {
        signal: request.signal,
      }),
    )
  },
  async readSentInvitations(request: InvitationListRequest): Promise<SentInvitationList> {
    return parseContract(
      sentInvitationListSchema,
      await sessionClient.authenticatedJson(invitationListPath('sent', request), {
        signal: request.signal,
      }),
    )
  },
  async sendInvitation({
    recipientProfileId,
    message,
  }: SendInvitationRequest): Promise<InvitationCreateResponse> {
    return parseContract(
      invitationCreateResponseSchema,
      await sessionClient.authenticatedJson('/matching/invitations', {
        method: 'POST',
        body: { recipient_profile_id: recipientProfileId, message },
      }),
    )
  },
  async acceptInvitation(invitationId: string): Promise<InvitationAcceptResponse> {
    const result = parseContract(
      invitationAcceptResponseSchema,
      await sessionClient.authenticatedJson(`/matching/invitations/${invitationId}/accept`, {
        method: 'POST',
      }),
    )
    if (result.invitation_id !== invitationId) throw new ApiError(200, 'invalidResponse')
    return result
  },
  declineInvitation(invitationId: string): Promise<InvitationMutationResponse> {
    return mutateInvitation(invitationId, 'decline', 'DECLINED')
  },
  cancelInvitation(invitationId: string): Promise<InvitationMutationResponse> {
    return mutateInvitation(invitationId, 'cancel', 'CANCELLED')
  },
  hideInvitation(invitationId: string): Promise<InvitationMutationResponse> {
    return mutateInvitation(invitationId, 'hide', 'ACCEPTED')
  },
}

export { matchingClient }
export type { InvitationListRequest, RecommendationRequest, SendInvitationRequest }
