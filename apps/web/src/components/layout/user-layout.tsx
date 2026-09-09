import { Outlet } from 'react-router'

function UserLayout() {
  return (
    <div className="min-h-screen bg-background text-foreground" data-layout="user">
      <Outlet />
    </div>
  )
}

export { UserLayout }
