import { Outlet } from 'react-router'

import { Footer } from '@/components/layout/footer'
import { Navbar } from '@/components/layout/navbar'
import { useSiteTheme } from '@/features/site-theme/site-theme'
import { useScrollToTop } from '@/hooks/use-scroll-to-top'

function PublicLayout() {
  useScrollToTop()
  const theme = useSiteTheme()

  return (
    <div
      className="flex min-h-screen flex-col bg-background text-foreground"
      data-layout="public"
      data-site-theme={theme}
    >
      <Navbar />
      <div className="flex-1">
        <Outlet />
      </div>
      <Footer />
    </div>
  )
}

export { PublicLayout }
