import { useId, useMemo, useState } from 'react'
import {
  CheckCircle2,
  CircleAlert,
  HeartHandshake,
  MailCheck,
  UserRoundCheck,
  Users,
  UserX,
  X,
} from 'lucide-react'
import { useTranslation } from 'react-i18next'

import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { DataTable, type DataTableColumn } from '@/components/ui/data-table'
import { Typography } from '@/components/ui/typography'
import {
  ADMIN_MATCHING_DEFAULT_PAGE_SIZE,
  type AdminMatchingParticipant,
  type AdminMatchingParticipantDetail as ParticipantDetailData,
  type AdminMatchingStats,
  type StudentType,
} from '@/features/admin-matching/admin-matching'
import {
  useAdminMatchingParticipantDetail,
  useAdminMatchingParticipants,
  useAdminMatchingStats,
} from '@/features/admin-matching/queries/use-admin-matching'
import { MatchingProfileDetails } from '@/features/matching/matching-profile-details'
import type { CatalogLocale } from '@/features/profile/profile-catalog'

const PAGE_SIZES = [10, 20, 50] as const
const controlClassName =
  'h-10 w-full min-w-0 rounded-md border border-input bg-background px-3 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50'

interface ParticipantView {
  page: number
  pageSize: number
  studentType: StudentType | null
  verified: boolean | null
  zeroBuddiesOnly: boolean
}

function catalogLocale(language: string | undefined): CatalogLocale {
  return language?.split('-')[0] === 'de' ? 'de' : 'en'
}

function displayName(value: string | null, unnamed: string): string {
  return value?.trim() || unnamed
}

function StatusValue({ value }: { value: boolean }) {
  const { t } = useTranslation()
  return (
    <span
      className={
        value
          ? 'inline-flex rounded-full bg-emerald-500/10 px-2 py-1 text-xs font-semibold text-emerald-700 dark:text-emerald-300'
          : 'inline-flex rounded-full bg-muted px-2 py-1 text-xs font-semibold text-muted-foreground'
      }
    >
      {t(value ? 'adminMatching.status.yes' : 'adminMatching.status.no')}
    </span>
  )
}

const statisticCards = [
  { id: 'participants', field: 'participant_count', Icon: Users },
  { id: 'verified', field: 'verified_participant_count', Icon: MailCheck },
  { id: 'activeMatches', field: 'active_match_count', Icon: HeartHandshake },
  { id: 'zeroBuddies', field: 'zero_buddy_participant_count', Icon: UserX },
] as const satisfies readonly {
  id: string
  field: keyof Omit<AdminMatchingStats, 'invitations'>
  Icon: typeof Users
}[]

function StatisticsSection({ query }: { query: ReturnType<typeof useAdminMatchingStats> }) {
  const { t } = useTranslation()
  const headingId = useId()

  return (
    <section aria-labelledby={headingId} className="space-y-4" aria-busy={query.isFetching}>
      <div className="flex flex-wrap items-center justify-between gap-3">
        <Typography as="h2" variant="h3" id={headingId}>
          {t('adminMatching.statistics.title')}
        </Typography>
        {query.isFetching && !query.isPending ? (
          <span role="status" className="text-sm text-muted-foreground">
            {t('adminMatching.statistics.updating')}
          </span>
        ) : null}
      </div>
      {query.isPending ? (
        <Card className="p-6 shadow-none">
          <p role="status">{t('adminMatching.statistics.loading')}</p>
        </Card>
      ) : query.isError ? (
        <Card className="border-destructive/40 p-6 shadow-none">
          <div className="space-y-3">
            <p role="alert">{t('adminMatching.statistics.error')}</p>
            <Button type="button" variant="outline" onClick={() => void query.refetch()}>
              {t('adminMatching.retry')}
            </Button>
          </div>
        </Card>
      ) : (
        <div className="grid min-w-0 gap-4 sm:grid-cols-2 xl:grid-cols-5">
          {statisticCards.map(({ id, field, Icon }) => (
            <Card key={id} className="min-w-0 p-4 shadow-none">
              <div className="flex items-start gap-2 text-sm font-medium">
                <Icon aria-hidden="true" className="mt-0.5 size-4 shrink-0 text-primary" />
                <span className="break-words">{t(`adminMatching.statistics.${id}`)}</span>
              </div>
              <p className="mt-3 text-3xl font-semibold tabular-nums">{query.data[field]}</p>
            </Card>
          ))}
          <Card className="min-w-0 p-4 shadow-none">
            <div className="flex items-start gap-2 text-sm font-medium">
              <UserRoundCheck aria-hidden="true" className="mt-0.5 size-4 shrink-0 text-primary" />
              <span className="break-words">{t('adminMatching.statistics.invitations')}</span>
            </div>
            <dl className="mt-3 grid grid-cols-2 gap-x-3 gap-y-2 text-sm">
              {Object.entries(query.data.invitations).map(([state, count]) => (
                <div key={state}>
                  <dt className="text-muted-foreground">
                    {t(`adminMatching.invitationStates.${state}`)}
                  </dt>
                  <dd className="font-semibold tabular-nums">{count}</dd>
                </div>
              ))}
            </dl>
          </Card>
        </div>
      )}
    </section>
  )
}

function ParticipantDetail({
  profileId,
  locale,
  onClose,
}: {
  profileId: string
  locale: CatalogLocale
  onClose: () => void
}) {
  const { t } = useTranslation()
  const headingId = useId()
  const query = useAdminMatchingParticipantDetail({ profileId, locale })

  return (
    <Card
      role="region"
      aria-labelledby={headingId}
      className="min-w-0 border-primary/25 shadow-none"
    >
      <CardHeader className="flex-row items-start justify-between gap-3 space-y-0">
        <div className="min-w-0 space-y-1">
          <CardTitle id={headingId}>{t('adminMatching.detail.title')}</CardTitle>
          <p className="text-sm text-muted-foreground">{t('adminMatching.detail.description')}</p>
        </div>
        <Button
          type="button"
          variant="ghost"
          size="icon"
          aria-label={t('adminMatching.detail.close')}
          onClick={onClose}
        >
          <X aria-hidden="true" />
        </Button>
      </CardHeader>
      <CardContent aria-busy={query.isFetching}>
        {query.isPending ? (
          <p role="status">{t('adminMatching.detail.loading')}</p>
        ) : query.isError ? (
          <div className="space-y-3">
            <p role="alert">{t('adminMatching.detail.error')}</p>
            <Button type="button" variant="outline" onClick={() => void query.refetch()}>
              {t('adminMatching.retry')}
            </Button>
          </div>
        ) : (
          <ParticipantDetailContent detail={query.data} />
        )}
      </CardContent>
    </Card>
  )
}

function ParticipantDetailContent({ detail }: { detail: ParticipantDetailData }) {
  const { t } = useTranslation()
  const name = displayName(detail.profile.display_name, t('adminMatching.unnamed'))

  return (
    <div className="min-w-0 space-y-6">
      <div className="space-y-1">
        <Typography as="h3" variant="h4" className="break-words">
          {name}
        </Typography>
        <Typography variant="muted" className="break-words">
          {detail.profile.student_type
            ? t(`adminMatching.studentTypes.${detail.profile.student_type}`)
            : t('adminMatching.notShared')}
          {' · '}
          {detail.profile.major?.trim() || t('adminMatching.majorNotShared')}
        </Typography>
      </div>
      <dl className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        {[
          ['active', detail.is_active],
          ['verified', detail.email_verified],
          ['optIn', detail.matching_opt_in],
        ].map(([label, value]) => (
          <div key={String(label)} className="rounded-lg border p-3">
            <dt className="text-sm text-muted-foreground">{t(`adminMatching.columns.${label}`)}</dt>
            <dd className="mt-1">
              <StatusValue value={Boolean(value)} />
            </dd>
          </div>
        ))}
        <div className="rounded-lg border p-3">
          <dt className="text-sm text-muted-foreground">{t('adminMatching.columns.buddies')}</dt>
          <dd className="mt-1 text-lg font-semibold tabular-nums">{detail.buddy_count}</dd>
        </div>
      </dl>
      <MatchingProfileDetails profile={detail.profile} />
    </div>
  )
}

function AdminMatchingPage() {
  const { t, i18n } = useTranslation()
  const locale = catalogLocale(i18n.resolvedLanguage)
  const titleId = useId()
  const filtersId = useId()
  const [view, setView] = useState<ParticipantView>({
    page: 1,
    pageSize: ADMIN_MATCHING_DEFAULT_PAGE_SIZE,
    studentType: null,
    verified: null,
    zeroBuddiesOnly: false,
  })
  const [selectedProfileId, setSelectedProfileId] = useState<string | null>(null)
  const stats = useAdminMatchingStats()
  const participants = useAdminMatchingParticipants(view)
  const visiblePage = participants.isPlaceholderData ? undefined : participants.data
  const unavailable = participants.isFetching
  const hasFilters = view.studentType !== null || view.verified !== null || view.zeroBuddiesOnly
  const columns = useMemo<readonly DataTableColumn<AdminMatchingParticipant>[]>(
    () => [
      {
        id: 'name',
        header: t('adminMatching.columns.name'),
        accessor: (participant) =>
          displayName(participant.display_name, t('adminMatching.unnamed')),
      },
      {
        id: 'studentType',
        header: t('adminMatching.columns.studentType'),
        cell: (participant) =>
          participant.student_type
            ? t(`adminMatching.studentTypes.${participant.student_type}`)
            : t('adminMatching.notShared'),
      },
      {
        id: 'active',
        header: t('adminMatching.columns.active'),
        cell: (participant) => <StatusValue value={participant.is_active} />,
      },
      {
        id: 'verified',
        header: t('adminMatching.columns.verified'),
        cell: (participant) => <StatusValue value={participant.email_verified} />,
      },
      {
        id: 'optIn',
        header: t('adminMatching.columns.optIn'),
        cell: (participant) => <StatusValue value={participant.matching_opt_in} />,
      },
      {
        id: 'buddies',
        header: t('adminMatching.columns.buddies'),
        accessor: (participant) => participant.buddy_count,
      },
      {
        id: 'details',
        header: t('adminMatching.columns.details'),
        cell: (participant) => (
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={() => setSelectedProfileId(participant.profile_id)}
          >
            {t('adminMatching.viewDetails', {
              name: displayName(participant.display_name, t('adminMatching.unnamed')),
            })}
          </Button>
        ),
      },
    ],
    [t],
  )

  const updateFilter = (patch: Partial<ParticipantView>) => {
    setView((current) => ({ ...current, ...patch, page: 1 }))
  }

  return (
    <section aria-labelledby={titleId} className="min-w-0 space-y-8 py-6">
      <header className="space-y-2">
        <Typography as="h1" variant="h2" id={titleId} className="break-words">
          {t('adminMatching.title')}
        </Typography>
        <Typography variant="lead" className="max-w-3xl">
          {t('adminMatching.description')}
        </Typography>
        <p className="flex items-center gap-2 text-sm text-muted-foreground">
          <CheckCircle2 aria-hidden="true" className="size-4 shrink-0" />
          {t('adminMatching.readOnly')}
        </p>
      </header>

      <StatisticsSection query={stats} />

      <section aria-labelledby={filtersId} className="space-y-4">
        <Typography as="h2" variant="h3" id={filtersId}>
          {t('adminMatching.participants.title')}
        </Typography>
        <Card className="p-4 shadow-none">
          <div className="grid min-w-0 gap-4 sm:grid-cols-2 xl:grid-cols-4 xl:items-end">
            <div className="space-y-1">
              <label htmlFor={`${filtersId}-student-type`} className="text-sm font-medium">
                {t('adminMatching.filters.studentType')}
              </label>
              <select
                id={`${filtersId}-student-type`}
                className={controlClassName}
                value={view.studentType ?? ''}
                disabled={unavailable}
                onChange={(event) =>
                  updateFilter({ studentType: (event.target.value || null) as StudentType | null })
                }
              >
                <option value="">{t('adminMatching.filters.all')}</option>
                <option value="VIETNAMESE">{t('adminMatching.studentTypes.VIETNAMESE')}</option>
                <option value="INTERNATIONAL">
                  {t('adminMatching.studentTypes.INTERNATIONAL')}
                </option>
              </select>
            </div>
            <div className="space-y-1">
              <label htmlFor={`${filtersId}-verified`} className="text-sm font-medium">
                {t('adminMatching.filters.verification')}
              </label>
              <select
                id={`${filtersId}-verified`}
                className={controlClassName}
                value={view.verified === null ? '' : String(view.verified)}
                disabled={unavailable}
                onChange={(event) =>
                  updateFilter({
                    verified: event.target.value === '' ? null : event.target.value === 'true',
                  })
                }
              >
                <option value="">{t('adminMatching.filters.all')}</option>
                <option value="true">{t('adminMatching.filters.verified')}</option>
                <option value="false">{t('adminMatching.filters.unverified')}</option>
              </select>
            </div>
            <label className="flex min-h-10 items-center gap-3 rounded-md border px-3 text-sm font-medium">
              <input
                type="checkbox"
                checked={view.zeroBuddiesOnly}
                disabled={unavailable}
                onChange={(event) => updateFilter({ zeroBuddiesOnly: event.target.checked })}
              />
              {t('adminMatching.filters.zeroBuddies')}
            </label>
            <Button
              type="button"
              variant="outline"
              disabled={unavailable || !hasFilters}
              onClick={() =>
                setView((current) => ({
                  ...current,
                  page: 1,
                  studentType: null,
                  verified: null,
                  zeroBuddiesOnly: false,
                }))
              }
            >
              {t('adminMatching.filters.reset')}
            </Button>
          </div>
        </Card>

        {participants.isFetching && !participants.isPending ? (
          <p role="status" className="text-sm text-muted-foreground">
            {t('adminMatching.participants.updating')}
          </p>
        ) : null}

        <DataTable
          data={visiblePage?.items ?? []}
          columns={columns}
          getRowId={(participant) => participant.profile_id}
          caption={t('adminMatching.participants.caption')}
          searchable={false}
          pageSizeOptions={PAGE_SIZES}
          isLoading={participants.isPending || participants.isPlaceholderData}
          error={participants.isError ? t('adminMatching.participants.error') : null}
          onRetry={() => void participants.refetch()}
          emptyMessage={t('adminMatching.participants.empty')}
          serverPagination={{
            page: visiblePage?.page ?? view.page,
            pageSize: visiblePage?.page_size ?? view.pageSize,
            total: visiblePage?.total ?? 0,
            totalPages: visiblePage?.total_pages ?? 0,
            onPageChange: (page) => setView((current) => ({ ...current, page })),
            onPageSizeChange: (pageSize) =>
              setView((current) => ({ ...current, page: 1, pageSize })),
          }}
        />
      </section>

      {selectedProfileId ? (
        <ParticipantDetail
          profileId={selectedProfileId}
          locale={locale}
          onClose={() => setSelectedProfileId(null)}
        />
      ) : null}

      <p className="flex items-start gap-2 rounded-lg border border-border bg-muted/30 p-4 text-sm text-muted-foreground">
        <CircleAlert aria-hidden="true" className="mt-0.5 size-4 shrink-0" />
        {t('adminMatching.privacyNotice')}
      </p>
    </section>
  )
}

export { AdminMatchingPage }
