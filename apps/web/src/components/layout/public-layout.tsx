import { Outlet } from 'react-router'

function PublicLayout() {
  return (
    <div className="min-h-screen bg-background text-foreground" data-layout="public">
      <Outlet />
    </div>
  )
}

export { PublicLayout }
