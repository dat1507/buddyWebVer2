import { useId } from 'react'
import { useTranslation } from 'react-i18next'
import { Link, Outlet } from 'react-router'

import vguBuddyLogo from '@/assets/vgu-buddy-logo.png'
import { LanguageToggle } from '@/components/layout/language-toggle'
import { UserSidebarNavigation } from '@/components/layout/user-sidebar-navigation'
import { Card } from '@/components/ui/card'
import { Typography } from '@/components/ui/typography'

function UserLayout() {
  const { t } = useTranslation()
  const contentId = useId()

  return (
    <div className="bg-background text-foreground" data-layout="user">
      <a
        href={`#${contentId}`}
        className="sr-only rounded-md bg-primary px-4 py-2 font-medium text-primary-foreground focus:not-sr-only focus:absolute focus:left-4 focus:top-4 focus:z-50 focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 focus:ring-offset-background"
      >
        {t('userLayout.skipToContent')}
      </a>
      <div className="mx-auto grid w-full max-w-7xl gap-6 px-4 py-6 sm:px-6 lg:grid-cols-[16rem_minmax(0,1fr)] lg:items-start lg:px-8">
        <aside aria-label={t('userLayout.sidebarLabel')} className="min-w-0 lg:sticky lg:top-6">
          <Card className="space-y-5 p-4 sm:p-6">
            <div className="flex items-center justify-between gap-4 lg:flex-col lg:items-start">
              <Link
                to="/#home"
                aria-label={t('userLayout.backHome')}
                className="flex min-w-0 items-center gap-3 rounded-lg focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-vgu-orange"
              >
                <img
                  src={vguBuddyLogo}
                  alt=""
                  className="h-11 w-11 shrink-0 rounded-full object-cover"
                />
                <div className="min-w-0">
                  <Typography as="p" variant="small" className="truncate font-semibold">
                    VGU Buddy
                  </Typography>
                  <Typography variant="muted" className="mt-1">
                    {t('userLayout.backHome')}
                  </Typography>
                </div>
              </Link>
              <LanguageToggle />
            </div>
            <UserSidebarNavigation />
          </Card>
        </aside>
        <main
          id={contentId}
          aria-label={t('userLayout.contentLabel')}
          tabIndex={-1}
          className="min-w-0 focus:outline-none"
        >
          <Outlet />
        </main>
      </div>
    </div>
  )
}

export { UserLayout }
