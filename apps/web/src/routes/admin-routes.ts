import type { ComponentType } from 'react'
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

import { AdminOverviewPage } from '@/pages/admin/admin-overview-page'

type AdminRoute = {
  path: string
  title: string
  labelKey: string
  Icon: LucideIcon
  end?: boolean
} & ({ kind: 'placeholder' } | { kind: 'page'; Component: ComponentType })

// Part 20's canonical module paths share navigation and page-delivery metadata.
// Replace a placeholder only when its page task is accepted.
const adminRoutes: readonly AdminRoute[] = [
  {
    path: 'dashboard',
    title: 'Admin overview',
    labelKey: 'adminNavigation.overview',
    Icon: LayoutDashboard,
    end: true,
    kind: 'page',
    Component: AdminOverviewPage,
  },
  {
    path: 'users',
    title: 'User management',
    labelKey: 'adminNavigation.users',
    Icon: Users,
    kind: 'placeholder',
  },
  {
    path: 'matching',
    title: 'Matching management',
    labelKey: 'adminNavigation.matching',
    Icon: HeartHandshake,
    kind: 'placeholder',
  },
  {
    path: 'events',
    title: 'Event management',
    labelKey: 'adminNavigation.events',
    Icon: CalendarDays,
    kind: 'placeholder',
  },
  {
    path: 'event-sliders',
    title: 'Event sliders',
    labelKey: 'adminNavigation.eventSliders',
    Icon: Images,
    kind: 'placeholder',
  },
  {
    path: 'announcements',
    title: 'Announcements',
    labelKey: 'adminNavigation.announcements',
    Icon: Megaphone,
    kind: 'placeholder',
  },
  {
    path: 'knowledge-base',
    title: 'Knowledge base',
    labelKey: 'adminNavigation.knowledgeBase',
    Icon: BookOpen,
    kind: 'placeholder',
  },
  {
    path: 'campus',
    title: 'Campus management',
    labelKey: 'adminNavigation.campus',
    Icon: GraduationCap,
    kind: 'placeholder',
  },
  {
    path: 'analytics',
    title: 'Analytics',
    labelKey: 'adminNavigation.analytics',
    Icon: ChartNoAxesCombined,
    kind: 'placeholder',
  },
  {
    path: 'audit-log',
    title: 'Audit log',
    labelKey: 'adminNavigation.auditLog',
    Icon: ClipboardList,
    kind: 'placeholder',
  },
  {
    path: 'settings',
    title: 'Admin settings',
    labelKey: 'adminNavigation.settings',
    Icon: Settings,
    kind: 'placeholder',
  },
]

export { adminRoutes }
