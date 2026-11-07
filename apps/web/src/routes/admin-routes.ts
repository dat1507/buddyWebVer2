import type { ComponentType } from 'react'
import {
  BookOpen,
  CalendarDays,
  ClipboardList,
  HeartHandshake,
  Settings,
  RotateCcwKey,
  Users,
  type LucideIcon,
} from 'lucide-react'

import { AdminAuditLogPage } from '@/pages/admin/admin-audit-log-page'
import { AdminKnowledgePage } from '@/pages/admin/admin-knowledge-page'
import { AdminMatchingPage } from '@/pages/admin/admin-matching-page'
import { AdminSemesterPage } from '@/pages/admin/admin-semester-page'
import { AdminUsersPage } from '@/pages/admin/admin-users-page'
import { AdminEventsPage } from '@/pages/admin/admin-events-page'
import { adminEventsEnabled } from '@/config/launch-scope'

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
    path: 'users',
    title: 'User management',
    labelKey: 'adminNavigation.users',
    Icon: Users,
    kind: 'page',
    Component: AdminUsersPage,
  },
  {
    path: 'matching',
    title: 'Matching monitoring',
    labelKey: 'adminNavigation.matching',
    Icon: HeartHandshake,
    kind: 'page',
    Component: AdminMatchingPage,
  },
  {
    path: 'semesters',
    title: 'Semester management',
    labelKey: 'adminNavigation.semesters',
    Icon: RotateCcwKey,
    kind: 'page',
    Component: AdminSemesterPage,
  },
  ...(adminEventsEnabled
    ? ([
        {
          path: 'events',
          title: 'Event management',
          labelKey: 'adminNavigation.events',
          Icon: CalendarDays,
          kind: 'page',
          Component: AdminEventsPage,
        },
      ] satisfies readonly AdminRoute[])
    : []),
  {
    path: 'knowledge-base',
    title: 'Knowledge base',
    labelKey: 'adminNavigation.knowledgeBase',
    Icon: BookOpen,
    kind: 'page',
    Component: AdminKnowledgePage,
  },
  {
    path: 'audit-log',
    title: 'Audit log',
    labelKey: 'adminNavigation.auditLog',
    Icon: ClipboardList,
    kind: 'page',
    Component: AdminAuditLogPage,
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
