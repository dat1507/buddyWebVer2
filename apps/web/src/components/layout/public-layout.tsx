import { Outlet } from 'react-router'

import { Navbar } from '@/components/layout/navbar'

function PublicLayout() {
  return (
    <div className="min-h-screen bg-background text-foreground" data-layout="public">
      <Navbar />
      <Outlet />
    </div>
  )
}

export { PublicLayout }
