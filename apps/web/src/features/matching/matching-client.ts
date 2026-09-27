import { sessionClient } from '@/features/auth/session-client'
import {
  parseRecommendationList,
  type RecommendationList,
} from '@/features/matching/recommendation'
import type { CatalogLocale } from '@/features/profile/profile-catalog'

interface RecommendationRequest {
  locale: CatalogLocale
  page: number
  pageSize: number
  signal?: AbortSignal
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
}

export { matchingClient }
export type { RecommendationRequest }
