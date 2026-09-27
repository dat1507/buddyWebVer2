import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { profileClient } from '@/features/profile/profile-client'
import type { ProfilePreferenceSnapshot } from '@/features/profile/profile-catalog'
import type { OwnProfile } from '@/features/profile/profile'

const profileQueryKeys = {
  all: ['profile'] as const,
  own: ['profile', 'own'] as const,
  completion: ['profile', 'completion'] as const,
  preferences: ['profile', 'preferences'] as const,
}

function useOwnProfile() {
  return useQuery({
    queryKey: profileQueryKeys.own,
    queryFn: ({ signal }) => profileClient.readOwn(signal),
  })
}

function useProfileCompletion() {
  return useQuery({
    queryKey: profileQueryKeys.completion,
    queryFn: ({ signal }) => profileClient.readCompletion(signal),
  })
}

function useProfilePreferences() {
  return useQuery({
    queryKey: profileQueryKeys.preferences,
    queryFn: ({ signal }) => profileClient.readPreferences(signal),
  })
}

function useUpdateOwnProfile() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: profileClient.updateOwn,
    onSuccess: (profile) => {
      queryClient.setQueryData(profileQueryKeys.own, profile)
      queryClient.setQueryData<ProfilePreferenceSnapshot>(
        profileQueryKeys.preferences,
        (preferences) =>
          preferences ? Object.freeze({ ...preferences, version: profile.version }) : preferences,
      )
      void queryClient.invalidateQueries({ queryKey: profileQueryKeys.completion })
    },
  })
}

function useUpdateProfilePreferences() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: profileClient.updatePreferences,
    onSuccess: (result) => {
      queryClient.setQueryData(profileQueryKeys.preferences, result)
      queryClient.setQueryData<OwnProfile>(profileQueryKeys.own, (profile) =>
        profile
          ? Object.freeze({
              ...profile,
              version: result.version,
              interest_ids: result.interest_ids,
              languages: result.languages,
              preferences: { preferred_activity_ids: result.activity_ids },
            })
          : profile,
      )
    },
    onError: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: profileQueryKeys.own }),
        queryClient.invalidateQueries({ queryKey: profileQueryKeys.preferences }),
      ])
    },
    onSettled: async () => {
      await queryClient.invalidateQueries({ queryKey: profileQueryKeys.completion })
    },
  })
}

export {
  profileQueryKeys,
  useOwnProfile,
  useProfileCompletion,
  useProfilePreferences,
  useUpdateOwnProfile,
  useUpdateProfilePreferences,
}
