import { useId } from 'react'
import {
  CalendarClock,
  CalendarDays,
  HeartHandshake,
  MessageSquare,
  UserRound,
  Users,
} from 'lucide-react'
import { useTranslation } from 'react-i18next'

import { Card } from '@/components/ui/card'
import { Typography } from '@/components/ui/typography'

const metrics = [
  { id: 'totalUsers', Icon: Users },
  { id: 'activeMatches', Icon: HeartHandshake },
  { id: 'publishedEvents', Icon: CalendarDays },
  { id: 'aiQueriesToday', Icon: MessageSquare },
  { id: 'unmatchedStudents', Icon: UserRound },
  { id: 'upcomingEvents', Icon: CalendarClock },
] as const

function AdminOverviewPage() {
  const { t } = useTranslation()
  const titleId = useId()

  return (
    <section aria-labelledby={titleId} className="min-w-0 space-y-6 py-6">
      <header className="space-y-2">
        <Typography as="h1" variant="h3" id={titleId} className="break-words">
          {t('adminOverview.title')}
        </Typography>
        <Typography variant="muted">{t('adminOverview.description')}</Typography>
      </header>
      <dl className="grid min-w-0 gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {metrics.map(({ id, Icon }) => (
          <Card key={id} className="min-w-0 p-4 shadow-none">
            <dt className="flex items-start gap-2 text-sm font-medium">
              <Icon aria-hidden="true" className="mt-0.5 size-4 shrink-0 text-primary" />
              <span className="min-w-0 break-words">{t(`adminOverview.metrics.${id}`)}</span>
            </dt>
            <dd className="mt-3 space-y-1">
              <span aria-hidden="true" className="block text-3xl font-semibold leading-tight">
                —
              </span>
              <Typography as="span" variant="muted" className="block text-xs">
                {t('adminOverview.unavailable')}
              </Typography>
            </dd>
          </Card>
        ))}
      </dl>
    </section>
  )
}

export { AdminOverviewPage }
