import { useTranslation } from 'react-i18next'
import { AdminEventsTabs } from '@/features/recaps/admin-events-tabs'
import { useAdminEventStatistics } from '@/features/admin-statistics'
import { AdminStatistics } from '@/components/ui/admin-statistics'
import { Typography } from '@/components/ui/typography'
export function AdminEventStatisticsPage() {
  const { t } = useTranslation()
  const query = useAdminEventStatistics()
  return (
    <section className="min-w-0 space-y-6 py-6">
      <AdminEventsTabs />
      <Typography as="h1" variant="h2">
        {t('adminStatistics.title')}
      </Typography>
      <AdminStatistics
        query={query}
        metrics={[
          { label: t('adminStatistics.publishedEvents'), value: query.data?.published_events },
          { label: t('adminStatistics.upcomingEvents'), value: query.data?.upcoming_events },
        ]}
      />
    </section>
  )
}
