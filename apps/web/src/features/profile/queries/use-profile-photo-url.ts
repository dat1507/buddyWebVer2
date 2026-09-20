import { useQuery } from '@tanstack/react-query'

import { profileClient } from '@/features/profile/profile-client'
import type { ProfilePhotoUrl } from '@/features/profile/profile-photo'
import { profileQueryKeys } from '@/features/profile/queries/use-own-profile'

const PROFILE_PHOTO_RENEWAL_MARGIN_SECONDS = 30
const MINIMUM_RENEWAL_INTERVAL_MS = 1_000

const profilePhotoQueryKeys = {
  url: (photoId: string) => [...profileQueryKeys.all, 'photos', photoId, 'url'] as const,
}

function renewalDelay(data: ProfilePhotoUrl | undefined): number | false {
  if (!data) return false
  return Math.max(
    MINIMUM_RENEWAL_INTERVAL_MS,
    data.expiresAt - Date.now() - PROFILE_PHOTO_RENEWAL_MARGIN_SECONDS * 1_000,
  )
}

function staleTime(data: ProfilePhotoUrl | undefined): number {
  if (!data) return 0
  return Math.max(0, (data.expires_in - PROFILE_PHOTO_RENEWAL_MARGIN_SECONDS) * 1_000)
}

function useProfilePhotoUrl(photoId: string | null) {
  return useQuery({
    queryKey: profilePhotoQueryKeys.url(photoId ?? 'none'),
    queryFn: ({ signal }) => profileClient.readPhotoUrl(photoId!, signal),
    enabled: photoId !== null,
    staleTime: (query) => staleTime(query.state.data),
    refetchInterval: (query) => renewalDelay(query.state.data),
    refetchIntervalInBackground: false,
  })
}

export { profilePhotoQueryKeys, useProfilePhotoUrl }
