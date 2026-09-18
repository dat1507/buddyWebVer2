import { useId } from 'react'
import { useTranslation } from 'react-i18next'
import { matchPath, NavLink, useLocation } from 'react-router'

import { buttonVariants } from '@/components/ui/button-variants'
import { Typography } from '@/components/ui/typography'
import { cn } from '@/lib/utils'
import { userNavigationItems, type UserNavigationItem } from '@/routes/user-navigation'

function navigationClass(active: boolean) {
  return cn(
    buttonVariants({ variant: 'ghost', size: 'sm' }),
    'h-auto min-h-10 w-full justify-start whitespace-normal py-2 text-left',
    active && 'bg-primary/15 text-primary ring-1 ring-primary/40',
  )
}

function UserSidebarNavigation({
  items = userNavigationItems,
}: {
  items?: readonly UserNavigationItem[]
}) {
  const { t } = useTranslation()
  const { pathname } = useLocation()
  const unavailableId = useId()
  const hasUnavailableItems = items.some(({ available }) => !available)

  return (
    <nav aria-label={t('userNavigation.label')} className="min-w-0 space-y-3">
      {hasUnavailableItems ? (
        <Typography id={unavailableId} variant="muted" className="text-xs">
          {t('userNavigation.unavailableHint')}
        </Typography>
      ) : null}
      <ul className="grid min-w-0 gap-2 sm:grid-cols-2 lg:grid-cols-1">
        {items.map(({ id, labelKey, Icon, end = false, ...destination }) => {
          const current = !!destination.to && !!matchPath({ path: destination.to, end }, pathname)
          return (
            <li key={id} className="min-w-0">
              {destination.available ? (
                <NavLink
                  to={destination.to}
                  end={end}
                  className={({ isActive }) => navigationClass(isActive)}
                >
                  <Icon aria-hidden="true" />
                  <span className="min-w-0 break-words">{t(labelKey)}</span>
                </NavLink>
              ) : (
                <span
                  role="link"
                  aria-disabled="true"
                  aria-describedby={unavailableId}
                  aria-current={current ? 'page' : undefined}
                  className={cn(
                    navigationClass(current),
                    'cursor-not-allowed',
                    current
                      ? 'hover:bg-primary/15 hover:text-primary'
                      : 'text-muted-foreground hover:bg-transparent hover:text-muted-foreground',
                  )}
                >
                  <Icon aria-hidden="true" />
                  <span className="min-w-0">
                    <span className="block break-words">{t(labelKey)}</span>
                    <span className="block text-xs font-normal text-muted-foreground">
                      {t('userNavigation.comingSoon')}
                    </span>
                  </span>
                </span>
              )}
            </li>
          )
        })}
      </ul>
    </nav>
  )
}

export { UserSidebarNavigation }
