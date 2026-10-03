import { useQuery } from '@tanstack/react-query'

import { adminUsersClient, type AdminUserListRequest } from '@/features/admin-users/admin-users'

type AdminUserQueryRequest = Omit<AdminUserListRequest, 'signal'>

const adminUserKeys = {
  root: ['private', 'admin-users'] as const,
  list: ({ page, pageSize, search }: AdminUserQueryRequest) =>
    ['private', 'admin-users', 'list', { page, pageSize, search }] as const,
}

function useAdminUsers(request: AdminUserQueryRequest) {
  return useQuery({
    queryKey: adminUserKeys.list(request),
    queryFn: ({ signal }) => adminUsersClient.readUsers({ ...request, signal }),
    meta: { private: true },
  })
}

export { adminUserKeys, useAdminUsers }
