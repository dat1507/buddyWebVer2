import {
  CalendarDays,
  HeartHandshake,
  LayoutDashboard,
  Settings,
  SquarePen,
  UserRound,
  Users,
  type LucideIcon,
} from 'lucide-react'

import { userRoutes, type UserRoutePath } from '@/routes/user-routes'

type UserNavigationItem = {
  id: string
  labelKey: string
  Icon: LucideIcon
  end?: boolean
} & ({ available: true; to: `/user/${string}` } | { available: false; to?: `/user/${string}` })

const definitions: readonly {
  id: string
  route: UserRoutePath | null
  Icon: LucideIcon
  end?: boolean
}[] = [
  { id: 'dashboard', route: 'dashboard', Icon: LayoutDashboard, end: true },
  { id: 'myProfile', route: 'profile', Icon: UserRound, end: true },
  { id: 'editProfile', route: null, Icon: SquarePen },
  { id: 'matching', route: 'matching', Icon: Users },
  { id: 'myBuddy', route: 'buddy', Icon: HeartHandshake },
  { id: 'events', route: 'events', Icon: CalendarDays },
  { id: 'settings', route: 'settings', Icon: Settings },
]

const userNavigationItems: readonly UserNavigationItem[] = definitions.map(({ route, ...item }) => {
  const destination = userRoutes.find(({ path }) => path === route)
  const base = { ...item, labelKey: `userNavigation.${item.id}` }
  if (!destination) return { ...base, available: false }
  const to = `/user/${destination.path}` as const
  return destination.kind === 'page'
    ? { ...base, available: true, to }
    : { ...base, available: false, to }
})

export { userNavigationItems }
export type { UserNavigationItem }
