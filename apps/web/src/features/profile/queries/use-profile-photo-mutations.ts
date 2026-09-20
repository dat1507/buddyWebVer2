import { useMutation, useQueryClient, type QueryClient } from '@tanstack/react-query'

import { profileClient } from '@/features/profile/profile-client'
import { profileQueryKeys } from '@/features/profile/queries/use-own-profile'

async function refetchProfileState(queryClient: QueryClient) {
  await Promise.all([
    queryClient.invalidateQueries({ queryKey: profileQueryKeys.own }),
    queryClient.invalidateQueries({ queryKey: profileQueryKeys.completion }),
  ])
}

function useUploadProfilePhoto() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: profileClient.uploadPhoto,
    onSuccess: () => refetchProfileState(queryClient),
  })
}

function useRemoveProfilePhoto() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: profileClient.removePhoto,
    onSuccess: () => refetchProfileState(queryClient),
  })
}

export { useRemoveProfilePhoto, useUploadProfilePhoto }
