import { useEffect, useId, useMemo, useState } from 'react'
import { Search, X } from 'lucide-react'
import { useTranslation } from 'react-i18next'

import { Button } from '@/components/ui/button'
import { DataTable, type DataTableColumn } from '@/components/ui/data-table'
import { Typography } from '@/components/ui/typography'
import {
  ADMIN_USERS_DEFAULT_PAGE_SIZE,
  type AdminUserSummary,
} from '@/features/admin-users/admin-users'
import { useAdminUsers } from '@/features/admin-users/queries/use-admin-users'

const PAGE_SIZES = [10, 20, 50, 100] as const
const SEARCH_DEBOUNCE_MS = 300
const inputClassName =
  'h-10 w-full min-w-0 rounded-md border border-input bg-background pl-10 pr-10 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring'

function StatusBadge({ positive, label }: { positive: boolean; label: string }) {
  return (
    <span
      className={
        positive
          ? 'inline-flex rounded-full bg-emerald-500/10 px-2 py-1 text-xs font-semibold text-emerald-700 dark:text-emerald-300'
          : 'inline-flex rounded-full bg-muted px-2 py-1 text-xs font-semibold text-muted-foreground'
      }
    >
      {label}
    </span>
  )
}

function AdminUsersPage() {
  const { t, i18n } = useTranslation()
  const titleId = useId()
  const searchId = useId()
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(ADMIN_USERS_DEFAULT_PAGE_SIZE)
  const [searchInput, setSearchInput] = useState('')
  const [search, setSearch] = useState('')

  useEffect(() => {
    const timer = window.setTimeout(() => {
      setSearch(searchInput.trim())
      setPage(1)
    }, SEARCH_DEBOUNCE_MS)
    return () => window.clearTimeout(timer)
  }, [searchInput])

  const users = useAdminUsers({ page, pageSize, search })
  const lastPage = Math.max(1, users.data?.total_pages ?? 1)
  const isRecoveringPage = Boolean(users.data && page > lastPage)

  useEffect(() => {
    if (!users.data || page <= lastPage) return
    const timer = window.setTimeout(() => setPage((current) => Math.min(current, lastPage)), 0)
    return () => window.clearTimeout(timer)
  }, [lastPage, page, users.data])

  const language = i18n.resolvedLanguage ?? 'en'
  const unavailable = t('adminUsers.unavailable')
  const columns = useMemo<readonly DataTableColumn<AdminUserSummary>[]>(
    () => [
      {
        id: 'name',
        header: t('adminUsers.columns.name'),
        accessor: (user) => user.profile?.display_name ?? user.profile?.full_name ?? unavailable,
        cell: (user) => {
          const displayName = user.profile?.display_name?.trim()
          const fullName = user.profile?.full_name?.trim()
          return (
            <div className="space-y-1">
              <p className="font-medium">{displayName || fullName || unavailable}</p>
              {displayName && fullName && displayName !== fullName ? (
                <p className="text-xs text-muted-foreground">{fullName}</p>
              ) : null}
            </div>
          )
        },
      },
      {
        id: 'email',
        header: t('adminUsers.columns.email'),
        accessor: (user) => user.email,
      },
      {
        id: 'studentType',
        header: t('adminUsers.columns.studentType'),
        accessor: (user) =>
          user.profile?.student_type
            ? t(`adminUsers.studentTypes.${user.profile.student_type}`)
            : unavailable,
      },
      {
        id: 'profile',
        header: t('adminUsers.columns.profile'),
        accessor: (user) => (user.profile ? 'available' : 'missing'),
        cell: (user) => (
          <StatusBadge
            positive={Boolean(user.profile)}
            label={t(
              user.profile ? 'adminUsers.status.profileAvailable' : 'adminUsers.status.noProfile',
            )}
          />
        ),
      },
      {
        id: 'verified',
        header: t('adminUsers.columns.verified'),
        accessor: (user) => user.email_verified,
        cell: (user) => (
          <StatusBadge
            positive={user.email_verified}
            label={t(
              user.email_verified ? 'adminUsers.status.verified' : 'adminUsers.status.unverified',
            )}
          />
        ),
      },
      {
        id: 'account',
        header: t('adminUsers.columns.account'),
        accessor: (user) => user.is_active,
        cell: (user) => (
          <StatusBadge
            positive={user.is_active}
            label={t(user.is_active ? 'adminUsers.status.active' : 'adminUsers.status.inactive')}
          />
        ),
      },
      {
        id: 'created',
        header: t('adminUsers.columns.created'),
        accessor: (user) => user.created_at,
        cell: (user) =>
          new Intl.DateTimeFormat(language, { dateStyle: 'medium', timeZone: 'UTC' }).format(
            new Date(user.created_at),
          ),
      },
    ],
    [language, t, unavailable],
  )

  const pendingSearch = searchInput.trim() !== search
  const loading = users.isPending || pendingSearch || isRecoveringPage
  const data = isRecoveringPage ? [] : (users.data?.items ?? [])

  return (
    <section aria-labelledby={titleId} className="min-w-0 space-y-6 py-6">
      <header className="space-y-2">
        <Typography as="h1" variant="h2" id={titleId} className="break-words text-3xl sm:text-4xl">
          {t('adminUsers.title')}
        </Typography>
        <Typography variant="lead" className="max-w-3xl">
          {t('adminUsers.description')}
        </Typography>
      </header>

      <div className="min-w-0 space-y-1">
        <label htmlFor={searchId} className="text-sm font-medium">
          {t('adminUsers.search.label')}
        </label>
        <div className="relative max-w-2xl">
          <Search
            aria-hidden="true"
            className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground"
          />
          <input
            id={searchId}
            type="search"
            value={searchInput}
            placeholder={t('adminUsers.search.placeholder')}
            className={inputClassName}
            onChange={(event) => setSearchInput(event.target.value)}
          />
          {searchInput ? (
            <Button
              type="button"
              variant="ghost"
              size="icon"
              className="absolute right-0 top-0"
              aria-label={t('adminUsers.search.clear')}
              onClick={() => {
                setSearchInput('')
                setSearch('')
                setPage(1)
              }}
            >
              <X aria-hidden="true" className="size-4" />
            </Button>
          ) : null}
        </div>
        <p className="text-sm text-muted-foreground">{t('adminUsers.search.help')}</p>
      </div>

      <DataTable
        data={data}
        columns={columns}
        getRowId={(user) => user.id}
        caption={t('adminUsers.caption')}
        searchable={false}
        isLoading={loading}
        error={users.isError && !pendingSearch ? t('adminUsers.error') : null}
        onRetry={() => void users.refetch()}
        emptyMessage={search ? t('adminUsers.noResults') : t('adminUsers.empty')}
        pageSizeOptions={PAGE_SIZES}
        serverPagination={{
          page,
          pageSize,
          total: users.data?.total ?? 0,
          totalPages: users.data?.total_pages ?? 0,
          onPageChange: setPage,
          onPageSizeChange: (nextPageSize) => {
            setPageSize(nextPageSize)
            setPage(1)
          },
        }}
      />
    </section>
  )
}

export { AdminUsersPage }
