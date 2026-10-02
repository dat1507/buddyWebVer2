import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { adminSemestersClient, type ExecuteInput } from '@/features/admin-semesters/admin-semesters'

const adminSemesterKeys = {
  root: ['private', 'admin-semesters'] as const,
  status: ['private', 'admin-semesters', 'status'] as const,
  resetPreflight: ['private', 'admin-semesters', 'reset-preflight'] as const,
  restorePreflight: (operationId: string) =>
    ['private', 'admin-semesters', 'restore-preflight', operationId] as const,
}

function useSemesterStatus() {
  return useQuery({
    queryKey: adminSemesterKeys.status,
    queryFn: ({ signal }) => adminSemestersClient.readStatus(signal),
    meta: { private: true },
    refetchInterval: (query) => {
      const data = query.state.data
      return data?.reset_operation?.state === 'RUNNING' ||
        data?.restore_operation?.state === 'RUNNING'
        ? 5_000
        : false
    },
  })
}

function useResetPreflight(enabled: boolean) {
  return useQuery({
    queryKey: adminSemesterKeys.resetPreflight,
    queryFn: ({ signal }) => adminSemestersClient.readResetPreflight(signal),
    enabled,
    meta: { private: true },
  })
}

function useRestorePreflight(operationId: string | null, enabled: boolean) {
  return useQuery({
    queryKey: adminSemesterKeys.restorePreflight(operationId ?? 'none'),
    queryFn: ({ signal }) => adminSemestersClient.readRestorePreflight(operationId!, signal),
    enabled: enabled && operationId !== null,
    meta: { private: true },
  })
}

function useLifecycleMutation(work: () => Promise<void>) {
  const client = useQueryClient()
  return useMutation({
    mutationFn: work,
    onSuccess: async () => {
      await client.invalidateQueries({ queryKey: adminSemesterKeys.root })
    },
  })
}

function usePrepareReset() {
  return useLifecycleMutation(() => adminSemestersClient.prepareReset())
}

function usePrepareRestore() {
  return useLifecycleMutation(() => adminSemestersClient.prepareRestore())
}

function useExecuteReset() {
  const client = useQueryClient()
  return useMutation({
    mutationFn: (input: ExecuteInput) => adminSemestersClient.executeReset(input),
    onSuccess: async () => client.invalidateQueries({ queryKey: adminSemesterKeys.root }),
  })
}

function useExecuteRestore() {
  const client = useQueryClient()
  return useMutation({
    mutationFn: (input: ExecuteInput) => adminSemestersClient.executeRestore(input),
    onSuccess: async () => client.invalidateQueries({ queryKey: adminSemesterKeys.root }),
  })
}

export {
  adminSemesterKeys,
  useExecuteReset,
  useExecuteRestore,
  usePrepareReset,
  usePrepareRestore,
  useResetPreflight,
  useRestorePreflight,
  useSemesterStatus,
}
