import { keepPreviousData, useQuery } from '@tanstack/react-query'

import { matchingClient } from '@/features/matching/matching-client'
import type { CatalogLocale } from '@/features/profile/profile-catalog'

const matchingQueryKeys = {
  all: ['matching'] as const,
  recommendationsRoot: ['matching', 'recommendations'] as const,
  recommendations: (locale: CatalogLocale, page: number, pageSize: number) =>
    ['matching', 'recommendations', locale, page, pageSize] as const,
  invitations: ['matching', 'invitations'] as const,
  incomingInvitations: (locale: CatalogLocale) =>
    ['matching', 'invitations', 'incoming', locale] as const,
  sentInvitations: (locale: CatalogLocale) => ['matching', 'invitations', 'sent', locale] as const,
}

function useRecommendations({
  enabled,
  locale,
  page,
  pageSize,
}: {
  enabled: boolean
  locale: CatalogLocale
  page: number
  pageSize: number
}) {
  return useQuery({
    queryKey: matchingQueryKeys.recommendations(locale, page, pageSize),
    queryFn: ({ signal }) => matchingClient.readRecommendations({ locale, page, pageSize, signal }),
    enabled,
    placeholderData: keepPreviousData,
  })
}

export { matchingQueryKeys, useRecommendations }
