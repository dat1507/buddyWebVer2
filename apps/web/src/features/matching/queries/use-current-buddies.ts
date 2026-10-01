import { useInfiniteQuery } from '@tanstack/react-query'

import { CURRENT_BUDDIES_PAGE_SIZE } from '@/features/matching/current-buddy'
import type { CurrentBuddy, CurrentBuddyList } from '@/features/matching/current-buddy'
import { matchingClient } from '@/features/matching/matching-client'
import { matchingQueryKeys } from '@/features/matching/queries/use-recommendations'
import type { CatalogLocale } from '@/features/profile/profile-catalog'

function useCurrentBuddies({ enabled, locale }: { enabled: boolean; locale: CatalogLocale }) {
  return useInfiniteQuery({
    queryKey: matchingQueryKeys.currentBuddies(locale),
    queryFn: ({ pageParam, signal }) =>
      matchingClient.readCurrentBuddies({
        locale,
        page: pageParam,
        pageSize: CURRENT_BUDDIES_PAGE_SIZE,
        signal,
      }),
    initialPageParam: 1,
    getNextPageParam: (lastPage) =>
      lastPage.page < lastPage.total_pages ? lastPage.page + 1 : undefined,
    enabled,
  })
}

function uniqueCurrentBuddies(pages: readonly CurrentBuddyList[] | undefined): CurrentBuddy[] {
  const seen = new Set<string>()
  return (pages ?? []).flatMap((page) =>
    page.items.filter(({ match_id: matchId }) => {
      if (seen.has(matchId)) return false
      seen.add(matchId)
      return true
    }),
  )
}

type CurrentBuddiesQuery = ReturnType<typeof useCurrentBuddies>

export { uniqueCurrentBuddies, useCurrentBuddies }
export type { CurrentBuddiesQuery }
