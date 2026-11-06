import type { UseQueryResult } from '@tanstack/react-query'
import { useTranslation } from 'react-i18next'
import { Card } from '@/components/ui/card'
import { Button } from '@/components/ui/button'

export function AdminStatistics({
  query,
  metrics,
}: {
  query: UseQueryResult<{ observed_at: string }>
  metrics: { label: string; value: number | undefined }[]
}) {
  const { t, i18n } = useTranslation()
  return (
    <section
      className="min-w-0 space-y-3"
      aria-label={t('adminStatistics.title')}
      aria-busy={query.isFetching}
    >
      {query.isPending ? <p role="status">{t('adminStatistics.loading')}</p> : null}
      {query.isError ? (
        <p role="alert">{t(query.data ? 'adminStatistics.stale' : 'adminStatistics.error')}</p>
      ) : null}
      {query.data ? (
        <>
          <div className="grid min-w-0 gap-4 sm:grid-cols-2">
            {metrics.map(({ label, value }) => (
              <Card key={label} className="min-w-0 p-4 shadow-none">
                <p className="break-words text-sm font-medium">{label}</p>
                <p className="mt-3 text-3xl font-semibold tabular-nums">{value}</p>
              </Card>
            ))}
          </div>
          <p className="text-sm text-muted-foreground">
            {t('adminStatistics.updated', {
              time: new Date(query.data.observed_at).toLocaleTimeString(i18n.language),
            })}
          </p>
        </>
      ) : null}
      <Button
        type="button"
        variant="outline"
        disabled={query.isFetching}
        onClick={() => void query.refetch({ cancelRefetch: false })}
      >
        {t('adminStatistics.refresh')}
      </Button>
    </section>
  )
}
