import { useTranslation } from 'react-i18next'
import { NavLink } from 'react-router'

import { buttonVariants } from '@/components/ui/button-variants'
import { Typography } from '@/components/ui/typography'
import { cn } from '@/lib/utils'
import { adminRoutes } from '@/routes/admin-routes'

function AdminSidebarNavigation() {
  const { t } = useTranslation()

  return (
    <nav aria-label={t('adminNavigation.label')} className="min-w-0 space-y-3">
      <Typography variant="muted" className="text-xs">
        {t('adminNavigation.scaffoldHint')}
      </Typography>
      <ul className="grid min-w-0 gap-2 sm:grid-cols-2 md:grid-cols-1">
        {adminRoutes.map(({ path, labelKey, Icon, end = false }) => (
          <li key={path} className="min-w-0">
            <NavLink
              to={`/admin/${path}`}
              end={end}
              className={({ isActive }) =>
                cn(
                  buttonVariants({ variant: 'ghost', size: 'sm' }),
                  'h-auto min-h-10 w-full justify-start whitespace-normal py-2 text-left',
                  isActive && 'bg-primary/15 text-primary ring-1 ring-primary/40',
                )
              }
            >
              <Icon aria-hidden="true" />
              <span className="min-w-0 break-words">{t(labelKey)}</span>
            </NavLink>
          </li>
        ))}
      </ul>
    </nav>
  )
}

export { AdminSidebarNavigation }
