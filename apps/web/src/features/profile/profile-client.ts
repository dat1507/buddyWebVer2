import { sessionClient } from '@/features/auth/session-client'
import {
  parseInterestCatalog,
  parseInterestSelection,
  parseLanguageCatalog,
  parseLanguageSelection,
} from '@/features/profile/profile-catalog'
import type {
  CatalogLocale,
  InterestCatalog,
  LanguageCatalog,
  ProfileSelectionsResult,
  ProfileSelectionsUpdate,
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

  async updateSelections(update: ProfileSelectionsUpdate): Promise<ProfileSelectionsResult> {
    let version = update.version
    let interestIds = update.interestIds
    let languages = update.languages

    if (update.updateInterests) {
      const result = parseInterestSelection(
        await sessionClient.authenticatedJson('/profile/interests', {
          method: 'PUT',
          body: { version, interest_ids: interestIds },
        }),
      )
      version = result.version
      interestIds = result.interest_ids
    }

    if (update.updateLanguages) {
      const result = parseLanguageSelection(
        await sessionClient.authenticatedJson('/profile/languages', {
          method: 'PUT',
          body: { version, languages },
        }),
      )
      version = result.version
      languages = result.languages
    }

    return { version, interest_ids: interestIds, languages }
  },
}

export { profileClient }
