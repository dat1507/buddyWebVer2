import { useQuery } from '@tanstack/react-query'

import { adminUsersClient, type AdminUserListRequest } from '@/features/admin-users/admin-users'

type AdminUserQueryRequest = Omit<AdminUserListRequest, 'signal'>

const adminUserKeys = {
  root: ['private', 'admin-users'] as const,
  list: ({ page, pageSize, search }: AdminUserQueryRequest) =>
    ['private', 'admin-users', 'list', { page, pageSize, search }] as const,
  detail: (userId: string) => ['private', 'admin-users', 'detail', userId] as const,
}

function useAdminUsers(request: AdminUserQueryRequest) {
  return useQuery({
    queryKey: adminUserKeys.list(request),
    queryFn: ({ signal }) => adminUsersClient.readUsers({ ...request, signal }),
    meta: { private: true },
  })
}

function useAdminUserDetail(userId: string | null) {
  return useQuery({
    queryKey: adminUserKeys.detail(userId ?? 'none'),
    queryFn: ({ signal }) => adminUsersClient.readUserDetail({ userId: userId!, signal }),
    enabled: userId !== null,
    meta: { private: true },
  })
}

export { adminUserKeys, useAdminUserDetail, useAdminUsers }
