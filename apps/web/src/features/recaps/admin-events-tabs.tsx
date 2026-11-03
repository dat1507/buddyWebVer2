import { NavLink } from 'react-router'
import { useTranslation } from 'react-i18next'

export function AdminEventsTabs({ recap = false }: { recap?: boolean }) {
  const { t } = useTranslation()
  // Route links provide native keyboard operation and retain selection on reload.
  return (
    <nav
      aria-label={t('adminEvents.title')}
      className="flex flex-wrap gap-2 border-b border-border pb-3"
    >
      <NavLink
        to="/admin/events"
        end
        aria-current={!recap ? 'page' : undefined}
        className={`rounded-full px-5 py-3 text-sm font-semibold ${!recap ? 'bg-primary text-primary-foreground' : 'bg-muted text-foreground'}`}
      >
        {t('recaps.sliderTab')}
      </NavLink>
      <NavLink
        to="/admin/events/recaps"
        className={`rounded-full px-5 py-3 text-sm font-semibold ${recap ? 'bg-primary text-primary-foreground' : 'bg-muted text-foreground'}`}
      >
        {t('recaps.recapTab')}
      </NavLink>
    </nav>
  )
}
