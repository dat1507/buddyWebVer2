import { useQuery } from '@tanstack/react-query'

import { profileClient } from '@/features/profile/profile-client'
import type { CatalogLocale } from '@/features/profile/profile-catalog'
import { profileQueryKeys } from '@/features/profile/queries/use-own-profile'

const profileCatalogQueryKeys = {
  all: [...profileQueryKeys.all, 'catalogs'] as const,
  interests: (locale: CatalogLocale) =>
    [...profileQueryKeys.all, 'catalogs', 'interests', locale] as const,
  languages: (locale: CatalogLocale) =>
    [...profileQueryKeys.all, 'catalogs', 'languages', locale] as const,
}

function useInterestCatalog(locale: CatalogLocale) {
  return useQuery({
    queryKey: profileCatalogQueryKeys.interests(locale),
    queryFn: ({ signal }) => profileClient.readInterests(locale, signal),
  })
}

function useLanguageCatalog(locale: CatalogLocale) {
  return useQuery({
    queryKey: profileCatalogQueryKeys.languages(locale),
    queryFn: ({ signal }) => profileClient.readLanguages(locale, signal),
  })
}

export { profileCatalogQueryKeys, useInterestCatalog, useLanguageCatalog }
