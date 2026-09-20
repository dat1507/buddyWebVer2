import { sessionClient } from '@/features/auth/session-client'
import { parseOwnProfile } from '@/features/profile/profile'
import type { OwnProfile, OwnProfileUpdate } from '@/features/profile/profile'

const profileClient = {
  async readOwn(signal?: AbortSignal): Promise<OwnProfile> {
    return parseOwnProfile(await sessionClient.authenticatedJson('/profile', { signal }))
  },

  async updateOwn(update: OwnProfileUpdate): Promise<OwnProfile> {
    return parseOwnProfile(
      await sessionClient.authenticatedJson('/profile', {
        method: 'PUT',
        body: update,
      }),
    )
  },
}

export { profileClient }
