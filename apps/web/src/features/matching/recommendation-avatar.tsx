import { useState } from 'react'
import { LoaderCircle, UserRound } from 'lucide-react'
import { useTranslation } from 'react-i18next'

import type { MatchingProfile } from '@/features/matching/recommendation'
import { useProfilePhotoUrl } from '@/features/profile/queries/use-profile-photo-url'

function RecommendationAvatar({ profile }: { profile: MatchingProfile }) {
  const { t } = useTranslation()
  const photo = useProfilePhotoUrl(profile.avatar.id)
  const [failedUrl, setFailedUrl] = useState<string | null>(null)
  const name = profile.display_name?.trim() || t('recommendedBuddies.unnamed')
  const showImage = photo.data && failedUrl !== photo.data.url

  return (
    <div className="relative aspect-square w-full overflow-hidden rounded-2xl bg-muted sm:w-40 sm:shrink-0">
      {showImage ? (
        <img
          src={photo.data.url}
          alt={t('recommendedBuddies.avatarAlt', { name })}
          width={profile.avatar.width}
          height={profile.avatar.height}
          loading="lazy"
          className="size-full object-cover"
          onError={() => setFailedUrl(photo.data.url)}
        />
      ) : (
        <div
          role="img"
          aria-label={t('recommendedBuddies.avatarUnavailable', { name })}
          className="flex size-full min-h-40 items-center justify-center text-muted-foreground"
        >
          {photo.isPending ? (
            <LoaderCircle
              aria-hidden="true"
              className="size-7 animate-spin motion-reduce:animate-none"
            />
          ) : (
            <UserRound aria-hidden="true" className="size-12" />
          )}
        </div>
      )}
    </div>
  )
}

export { RecommendationAvatar }
