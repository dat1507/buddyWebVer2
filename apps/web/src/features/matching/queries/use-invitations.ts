import { useInfiniteQuery, useMutation, useQueryClient } from '@tanstack/react-query'

import { INVITATION_PAGE_SIZE } from '@/features/matching/invitation'
import type {
  IncomingInvitation,
  IncomingInvitationList,
  SentInvitation,
  SentInvitationList,
} from '@/features/matching/invitation'
import { matchingClient } from '@/features/matching/matching-client'
import { matchingQueryKeys } from '@/features/matching/queries/use-recommendations'
import type { CatalogLocale } from '@/features/profile/profile-catalog'
import { profileQueryKeys } from '@/features/profile/queries/use-own-profile'
import { ApiError } from '@/lib/api'

function nextPage(lastPage: IncomingInvitationList | SentInvitationList): number | undefined {
  return lastPage.page < lastPage.total_pages ? lastPage.page + 1 : undefined
}

function useIncomingInvitations({ enabled, locale }: { enabled: boolean; locale: CatalogLocale }) {
  return useInfiniteQuery({
    queryKey: matchingQueryKeys.incomingInvitations(locale),
    queryFn: ({ pageParam, signal }) =>
      matchingClient.readIncomingInvitations({
        locale,
        page: pageParam,
        pageSize: INVITATION_PAGE_SIZE,
        signal,
      }),
    initialPageParam: 1,
    getNextPageParam: nextPage,
    enabled,
  })
}

function useSentInvitations({ enabled, locale }: { enabled: boolean; locale: CatalogLocale }) {
  return useInfiniteQuery({
    queryKey: matchingQueryKeys.sentInvitations(locale),
    queryFn: ({ pageParam, signal }) =>
      matchingClient.readSentInvitations({
        locale,
        page: pageParam,
        pageSize: INVITATION_PAGE_SIZE,
        signal,
      }),
    initialPageParam: 1,
    getNextPageParam: nextPage,
    enabled,
  })
}

function uniqueIncomingItems(
  pages: readonly IncomingInvitationList[] | undefined,
): IncomingInvitation[] {
  const seen = new Set<string>()
  return (pages ?? []).flatMap((page) =>
    page.items.filter(({ id }) => {
      if (seen.has(id)) return false
      seen.add(id)
      return true
    }),
  )
}

function uniqueSentItems(pages: readonly SentInvitationList[] | undefined): SentInvitation[] {
  const seen = new Set<string>()
  return (pages ?? []).flatMap((page) =>
    page.items.filter(({ id }) => {
      if (seen.has(id)) return false
      seen.add(id)
      return true
    }),
  )
}

function shouldReconcile(error: unknown): boolean {
  return (
    error instanceof ApiError &&
    ['conflict', 'notFound', 'forbidden', 'unauthorized'].includes(error.code)
  )
}

function useInvitationReconciliation() {
  const queryClient = useQueryClient()
  const reconcile = async (includeProfile = false) => {
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: matchingQueryKeys.invitations }),
      queryClient.invalidateQueries({ queryKey: matchingQueryKeys.recommendationsRoot }),
      queryClient.invalidateQueries({ queryKey: matchingQueryKeys.currentBuddiesRoot }),
      ...(includeProfile
        ? [queryClient.invalidateQueries({ queryKey: profileQueryKeys.completion })]
        : []),
    ])
  }
  return { queryClient, reconcile }
}

function useSendInvitation() {
  const { reconcile } = useInvitationReconciliation()
  return useMutation({
    mutationFn: (input: Parameters<typeof matchingClient.sendInvitation>[0]) =>
      matchingClient.sendInvitation(input),
    onSuccess: () => reconcile(),
    onError: (error) => (shouldReconcile(error) ? reconcile() : undefined),
  })
}

function useAcceptInvitation() {
  const { reconcile } = useInvitationReconciliation()
  return useMutation({
    mutationFn: (invitationId: string) => matchingClient.acceptInvitation(invitationId),
    onSuccess: () => reconcile(true),
    onError: (error) => (shouldReconcile(error) ? reconcile(true) : undefined),
  })
}

function useDeclineInvitation() {
  const { reconcile } = useInvitationReconciliation()
  return useMutation({
    mutationFn: (invitationId: string) => matchingClient.declineInvitation(invitationId),
    onSuccess: () => reconcile(),
    onError: (error) => (shouldReconcile(error) ? reconcile() : undefined),
  })
}

function useCancelInvitation() {
  const { reconcile } = useInvitationReconciliation()
  return useMutation({
    mutationFn: (invitationId: string) => matchingClient.cancelInvitation(invitationId),
    onSuccess: () => reconcile(),
    onError: (error) => (shouldReconcile(error) ? reconcile() : undefined),
  })
}

function useHideInvitation() {
  const { reconcile } = useInvitationReconciliation()
  return useMutation({
    mutationFn: (invitationId: string) => matchingClient.hideInvitation(invitationId),
    onSuccess: () => reconcile(),
    onError: (error) => (shouldReconcile(error) ? reconcile() : undefined),
  })
}

type IncomingInvitationsQuery = ReturnType<typeof useIncomingInvitations>
type SentInvitationsQuery = ReturnType<typeof useSentInvitations>

export {
  uniqueIncomingItems,
  uniqueSentItems,
  useAcceptInvitation,
  useCancelInvitation,
  useDeclineInvitation,
  useHideInvitation,
  useIncomingInvitations,
  useSendInvitation,
  useSentInvitations,
}
export type { IncomingInvitationsQuery, SentInvitationsQuery }
