import { Outlet } from 'react-router'

import { Footer } from '@/components/layout/footer'
import { Navbar } from '@/components/layout/navbar'

function PublicLayout() {
  return (
    <div className="flex min-h-screen flex-col bg-background text-foreground" data-layout="public">
      <Navbar />
      <div className="flex-1">
        <Outlet />
      </div>
      <Footer />
    </div>
  )
}

export { PublicLayout }
