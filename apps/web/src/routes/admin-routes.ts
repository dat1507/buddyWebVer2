import {
  BookOpen,
  CalendarDays,
  ChartNoAxesCombined,
  ClipboardList,
  GraduationCap,
  HeartHandshake,
  Images,
  LayoutDashboard,
  Megaphone,
  Settings,
  Users,
  type LucideIcon,
} from 'lucide-react'

type AdminRoute = {
  path: string
  title: string
  labelKey: string
  Icon: LucideIcon
  end?: boolean
}

// Part 20's canonical module paths. These destinations are guarded scaffolds;
// their business pages are delivered by the subsequent module tasks.
const adminRoutes: readonly AdminRoute[] = [
  {
    path: 'dashboard',
    title: 'Admin overview',
    labelKey: 'adminNavigation.overview',
    Icon: LayoutDashboard,
    end: true,
  },
  { path: 'users', title: 'User management', labelKey: 'adminNavigation.users', Icon: Users },
  {
    path: 'matching',
    title: 'Matching management',
    labelKey: 'adminNavigation.matching',
    Icon: HeartHandshake,
  },
  {
    path: 'events',
    title: 'Event management',
    labelKey: 'adminNavigation.events',
    Icon: CalendarDays,
  },
  {
    path: 'event-sliders',
    title: 'Event sliders',
    labelKey: 'adminNavigation.eventSliders',
    Icon: Images,
  },
  {
    path: 'announcements',
    title: 'Announcements',
    labelKey: 'adminNavigation.announcements',
    Icon: Megaphone,
  },
  {
    path: 'knowledge-base',
    title: 'Knowledge base',
    labelKey: 'adminNavigation.knowledgeBase',
    Icon: BookOpen,
  },
  {
    path: 'campus',
    title: 'Campus management',
    labelKey: 'adminNavigation.campus',
    Icon: GraduationCap,
  },
  {
    path: 'analytics',
    title: 'Analytics',
    labelKey: 'adminNavigation.analytics',
    Icon: ChartNoAxesCombined,
  },
  {
    path: 'audit-log',
    title: 'Audit log',
    labelKey: 'adminNavigation.auditLog',
    Icon: ClipboardList,
  },
  {
    path: 'settings',
    title: 'Admin settings',
    labelKey: 'adminNavigation.settings',
    Icon: Settings,
  },
]

export { adminRoutes }
