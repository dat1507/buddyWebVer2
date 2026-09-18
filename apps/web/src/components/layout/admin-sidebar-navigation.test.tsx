import { render, screen, within } from '@testing-library/react'
import { MemoryRouter } from 'react-router'
import { beforeEach, describe, expect, it } from 'vitest'

import { AdminSidebarNavigation } from '@/components/layout/admin-sidebar-navigation'
import i18n from '@/i18n'

const paths = [
  'dashboard',
  'users',
  'matching',
  'events',
  'event-sliders',
  'announcements',
  'knowledge-base',
  'campus',
  'analytics',
  'audit-log',
  'settings',
]
const locales = [
  [
    'en',
    'Administrator navigation',
    [
      'Overview',
      'Users',
      'Matching',
      'Events',
      'Event Sliders',
      'Announcements',
      'Knowledge Base',
      'Campus',
      'Analytics',
      'Audit Log',
      'Settings',
    ],
  ],
  [
    'de',
    'Administrationsnavigation',
    [
      'Übersicht',
      'Benutzer',
      'Zuordnung',
      'Veranstaltungen',
      'Veranstaltungsslider',
      'Mitteilungen',
      'Wissensdatenbank',
      'Campus',
      'Analysen',
      'Audit-Protokoll',
      'Einstellungen',
    ],
  ],
] as const

describe('ADMIN-002 module navigation', () => {
  beforeEach(async () => {
    await i18n.changeLanguage('en')
  })

  it.each(locales)(
    'provides eleven named native module links in %s',
    async (language, name, labels) => {
      await i18n.changeLanguage(language)
      render(
        <MemoryRouter initialEntries={['/admin/dashboard']}>
          <AdminSidebarNavigation />
        </MemoryRouter>,
      )
      const nav = screen.getByRole('navigation', { name })
      expect(within(nav).getAllByRole('link')).toHaveLength(11)
      labels.forEach((label, index) => {
        const link = within(nav).getByRole('link', { name: label })
        expect(link.tagName).toBe('A')
        expect(link).toHaveAttribute('href', `/admin/${paths[index]}`)
        expect(link).not.toHaveAttribute('aria-disabled')
        expect(link).not.toHaveAttribute('tabindex', '-1')
        expect(link.querySelector('svg')).toHaveAttribute('aria-hidden', 'true')
      })
    },
  )

  it.each([
    ['/admin/dashboard?period=week#summary', 'Overview'],
    ['/admin/users/123/edit?tab=roles#form', 'Users'],
    ['/admin/event-sliders/123/edit', 'Event Sliders'],
    ['/admin/events/new', 'Events'],
    ['/admin/users-archive', null],
    ['/admin/dashboard/detail', null],
  ])('marks only the current module for %s', (path, label) => {
    // Nested paths are routing fixtures for the future module pages, not delivered pages.
    render(
      <MemoryRouter initialEntries={[path]}>
        <AdminSidebarNavigation />
      </MemoryRouter>,
    )
    const nav = screen.getByRole('navigation', { name: 'Administrator navigation' })
    const current = nav.querySelectorAll('[aria-current="page"]')
    expect(current).toHaveLength(label ? 1 : 0)
    if (label) {
      const link = within(nav).getByRole('link', { name: label })
      expect(current[0]).toBe(link)
      expect(link).toHaveClass('bg-primary/15', 'text-primary')
    }
  })
})
