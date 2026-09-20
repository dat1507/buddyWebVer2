import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { profileClient } from '@/features/profile/profile-client'
import type { OwnProfile } from '@/features/profile/profile'

const profileQueryKeys = {
  all: ['profile'] as const,
  own: ['profile', 'own'] as const,
  completion: ['profile', 'completion'] as const,
}

function useOwnProfile() {
  return useQuery({
    queryKey: profileQueryKeys.own,
    queryFn: ({ signal }) => profileClient.readOwn(signal),
  })
}

function useUpdateOwnProfile() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: profileClient.updateOwn,
    onSuccess: (profile) => {
      queryClient.setQueryData(profileQueryKeys.own, profile)
      void queryClient.invalidateQueries({ queryKey: profileQueryKeys.completion })
    },
  })
}

function useUpdateProfileSelections() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: profileClient.updateSelections,
    onSuccess: (result) => {
      queryClient.setQueryData<OwnProfile>(profileQueryKeys.own, (profile) =>
        profile
          ? Object.freeze({
              ...profile,
              version: result.version,
              interest_ids: result.interest_ids,
              languages: result.languages,
            })
          : profile,
      )
    },
    onError: async () => {
      await queryClient.invalidateQueries({ queryKey: profileQueryKeys.own })
    },
    onSettled: async () => {
      await queryClient.invalidateQueries({ queryKey: profileQueryKeys.completion })
    },
  })
}

export { profileQueryKeys, useOwnProfile, useUpdateOwnProfile, useUpdateProfileSelections }
