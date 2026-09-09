import { Outlet } from 'react-router'

function AdminLayout() {
  return (
    <div className="min-h-screen bg-background text-foreground" data-layout="admin">
      <Outlet />
    </div>
  )
}

export { AdminLayout }
