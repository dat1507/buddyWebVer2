import { sessionClient } from '@/features/auth/session-client'
import {
  parseActivityCatalog,
  parseInterestCatalog,
  parseLanguageCatalog,
  parseProfilePreferenceSnapshot,
} from '@/features/profile/profile-catalog'
import type {
  ActivityCatalog,
  CatalogLocale,
  InterestCatalog,
  LanguageCatalog,
  ProfilePreferenceSnapshot,
  ProfilePreferenceUpdate,
} from '@/features/profile/profile-catalog'
import { parseProfilePhoto, parseProfilePhotoUrl } from '@/features/profile/profile-photo'
import type { ProfilePhoto, ProfilePhotoUrl } from '@/features/profile/profile-photo'
import { parseProfileCompletion } from '@/features/profile/profile-completion'
import type { ProfileCompletion } from '@/features/profile/profile-completion'
import { parseOwnProfile } from '@/features/profile/profile'
import type {
  OnboardingPreferencesUpdate,
  OwnProfile,
  OwnProfileUpdate,
} from '@/features/profile/profile'

const profileClient = {
  async readOwn(signal?: AbortSignal): Promise<OwnProfile> {
    return parseOwnProfile(await sessionClient.authenticatedJson('/profile', { signal }))
  },

  async updateOwn(update: OwnProfileUpdate | OnboardingPreferencesUpdate): Promise<OwnProfile> {
    return parseOwnProfile(
      await sessionClient.authenticatedJson('/profile', {
        method: 'PUT',
        body: update,
      }),
    )
  },

  async readCompletion(signal?: AbortSignal): Promise<ProfileCompletion> {
    return parseProfileCompletion(
      await sessionClient.authenticatedJson('/profile/completion', { signal }),
    )
  },

  async readInterests(locale: CatalogLocale, signal?: AbortSignal): Promise<InterestCatalog> {
    return parseInterestCatalog(
      await sessionClient.authenticatedJson(`/interests?locale=${locale}`, { signal }),
      locale,
    )
  },

  async readLanguages(locale: CatalogLocale, signal?: AbortSignal): Promise<LanguageCatalog> {
    return parseLanguageCatalog(
      await sessionClient.authenticatedJson(`/languages?locale=${locale}`, { signal }),
      locale,
    )
  },

  async readActivities(locale: CatalogLocale, signal?: AbortSignal): Promise<ActivityCatalog> {
    return parseActivityCatalog(
      await sessionClient.authenticatedJson(`/activities?locale=${locale}`, { signal }),
      locale,
    )
  },

  async readPreferences(signal?: AbortSignal): Promise<ProfilePreferenceSnapshot> {
    return parseProfilePreferenceSnapshot(
      await sessionClient.authenticatedJson('/profile/preferences', { signal }),
    )
  },

  async readPhotoUrl(photoId: string, signal?: AbortSignal): Promise<ProfilePhotoUrl> {
    return parseProfilePhotoUrl(
      await sessionClient.authenticatedJson(`/profile/photos/${photoId}/url`, { signal }),
      photoId,
    )
  },

  async uploadPhoto(file: File): Promise<ProfilePhoto> {
    return parseProfilePhoto(
      await sessionClient.authenticatedJson('/profile/photos', {
        method: 'POST',
        binaryBody: file,
        contentType: file.type || 'application/octet-stream',
      }),
    )
  },

  async removePhoto(photoId: string): Promise<void> {
    await sessionClient.authenticatedJson(`/profile/photos/${photoId}`, {
      method: 'DELETE',
    })
  },

  async updatePreferences(update: ProfilePreferenceUpdate): Promise<ProfilePreferenceSnapshot> {
    return parseProfilePreferenceSnapshot(
      await sessionClient.authenticatedJson('/profile/preferences', {
        method: 'PUT',
        body: update,
      }),
    )
  },
}

export { profileClient }
