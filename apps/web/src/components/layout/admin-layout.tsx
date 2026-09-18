import { useId } from 'react'
import { useTranslation } from 'react-i18next'
import { Outlet } from 'react-router'

import vguBuddyLogo from '@/assets/vgu-buddy-logo.png'
import { LanguageToggle } from '@/components/layout/language-toggle'
import { Card } from '@/components/ui/card'
import { Typography } from '@/components/ui/typography'

function AdminLayout() {
  const { t } = useTranslation()
  const contentId = useId()

  return (
    <div className="min-h-screen bg-background text-foreground" data-layout="admin">
      <a
        href={`#${contentId}`}
        className="sr-only rounded-md bg-primary px-4 py-2 font-medium text-primary-foreground focus:not-sr-only focus:absolute focus:left-4 focus:top-4 focus:z-50 focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 focus:ring-offset-background"
      >
        {t('adminLayout.skipToContent')}
      </a>
      <div className="mx-auto grid w-full max-w-[96rem] gap-4 px-4 py-4 sm:px-6 md:grid-cols-[14rem_minmax(0,1fr)] md:items-start lg:px-8">
        <aside aria-label={t('adminLayout.sidebarLabel')} className="min-w-0 md:sticky md:top-4">
          <Card className="border-primary/25 bg-zinc-950 p-4 shadow-none">
            <div className="flex flex-wrap items-start justify-between gap-3 md:flex-col">
              <div className="flex min-w-0 items-start gap-3">
                <img
                  src={vguBuddyLogo}
                  alt=""
                  className="h-10 w-10 shrink-0 rounded-full object-cover"
                />
                <div className="min-w-0 space-y-2">
                  <Typography as="p" variant="small" className="break-words font-semibold">
                    VGU Buddy
                  </Typography>
                  <Typography
                    variant="small"
                    className="inline-block rounded-md border border-primary/40 bg-primary/10 px-2 py-1 text-xs font-semibold text-primary"
                  >
                    {t('adminLayout.badge')}
                  </Typography>
                </div>
              </div>
              <LanguageToggle />
            </div>
          </Card>
        </aside>
        <main
          id={contentId}
          aria-label={t('adminLayout.contentLabel')}
          tabIndex={-1}
          className="min-w-0 focus:outline-none"
        >
          <Outlet />
        </main>
      </div>
    </div>
  )
}

export { AdminLayout }
