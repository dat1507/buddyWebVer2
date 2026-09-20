import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { profileClient } from '@/features/profile/profile-client'

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

export { profileQueryKeys, useOwnProfile, useUpdateOwnProfile }
