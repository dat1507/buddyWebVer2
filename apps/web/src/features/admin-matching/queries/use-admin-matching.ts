import { statisticsPolling } from '@/features/admin-statistics'
import { useAuthStore } from '@/stores/auth-store'
import { keepPreviousData, useQuery } from '@tanstack/react-query'

import {
  adminMatchingClient,
  type AdminMatchingParticipantRequest,
} from '@/features/admin-matching/admin-matching'
import type { CatalogLocale } from '@/features/profile/profile-catalog'

const adminMatchingQueryKeys = {
  root: ['private', 'admin-matching'] as const,
  stats: ['private', 'admin-matching', 'stats'] as const,
  participants: (request: Omit<AdminMatchingParticipantRequest, 'signal'>) =>
    [
      'private',
      'admin-matching',
      'participants',
      request.page,
      request.pageSize,
      request.studentType,
      request.verified,
      request.zeroBuddiesOnly,
    ] as const,
  participantDetail: (profileId: string, locale: CatalogLocale) =>
    ['private', 'admin-matching', 'participant', profileId, locale] as const,
}

function useAdminMatchingStats() {
  const enabled = useAuthStore(
    (state) => state.status === 'authenticated' && state.role === 'ADMIN',
  )
  return useQuery({
    ...statisticsPolling,
    enabled,
    queryKey: adminMatchingQueryKeys.stats,
    queryFn: ({ signal }) => adminMatchingClient.readStats(signal),
    meta: { private: true },
  })
}

function useAdminMatchingParticipants(request: Omit<AdminMatchingParticipantRequest, 'signal'>) {
  return useQuery({
    queryKey: adminMatchingQueryKeys.participants(request),
    queryFn: ({ signal }) => adminMatchingClient.readParticipants({ ...request, signal }),
    placeholderData: keepPreviousData,
    meta: { private: true },
  })
}

function useAdminMatchingParticipantDetail({
  profileId,
  locale,
}: {
  profileId: string | null
  locale: CatalogLocale
}) {
  return useQuery({
    queryKey: adminMatchingQueryKeys.participantDetail(profileId ?? 'none', locale),
    queryFn: ({ signal }) =>
      adminMatchingClient.readParticipantDetail({ profileId: profileId!, locale, signal }),
    enabled: profileId !== null,
    meta: { private: true },
  })
}

export {
  adminMatchingQueryKeys,
  useAdminMatchingParticipantDetail,
  useAdminMatchingParticipants,
  useAdminMatchingStats,
}
