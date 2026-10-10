import { act, render, screen, within } from '@testing-library/react'
import { beforeEach, describe, expect, it } from 'vitest'

import i18n from '@/i18n'
import { adminEventsEnabled } from '@/config/launch-scope'
import { AdminOverviewPage } from '@/pages/admin/admin-overview-page'

const locales = [
  [
    'en',
    'Admin overview',
    'Statistics are not available yet.',
    'Not available',
    [
      'Total Users',
      'Active Matches',
      ...(adminEventsEnabled ? ['Published Events'] : []),
      'AI Queries Today',
      'Unmatched Students',
      ...(adminEventsEnabled ? ['Upcoming Events'] : []),
    ],
  ],
  [
    'de',
    'Administrationsübersicht',
    'Statistiken sind noch nicht verfügbar.',
    'Nicht verfügbar',
    [
      'Benutzer insgesamt',
      'Aktive Zuordnungen',
      ...(adminEventsEnabled ? ['Veröffentlichte Veranstaltungen'] : []),
      'KI-Anfragen heute',
      'Studierende ohne Zuordnung',
      ...(adminEventsEnabled ? ['Bevorstehende Veranstaltungen'] : []),
    ],
  ],
] as const

describe('ADMIN-003 overview placeholders', () => {
  beforeEach(async () => {
    await i18n.changeLanguage('en')
  })

  it.each(locales)(
    'presents the configured named statistics as unavailable in %s',
    async (language, title, description, unavailable, labels) => {
      await i18n.changeLanguage(language)
      render(<AdminOverviewPage />)
      const region = screen.getByRole('region', { name: title })
      expect(within(region).getByRole('heading', { level: 1, name: title })).toBeVisible()
      expect(within(region).getByText(description)).toBeVisible()
      expect(
        within(region)
          .getAllByRole('term')
          .map((term) => term.textContent),
      ).toEqual(labels)
      const values = within(region).getAllByRole('definition')
      expect(values).toHaveLength(labels.length)
      values.forEach((value) => {
        expect(within(value).getByText(unavailable)).toBeVisible()
        expect(within(value).getByText('—')).toHaveAttribute('aria-hidden', 'true')
        expect(value.textContent).not.toMatch(/\d/)
      })
      expect(region.querySelectorAll('svg[aria-hidden="true"]')).toHaveLength(labels.length)
      expect(within(region).queryByRole('progressbar')).not.toBeInTheDocument()
      expect(region.querySelector('[aria-busy="true"]')).toBeNull()
      expect(screen.queryByRole('main')).not.toBeInTheDocument()
    },
  )

  it('updates the overview language without replacing its region or metric definitions', async () => {
    render(<AdminOverviewPage />)
    const region = screen.getByRole('region', { name: 'Admin overview' })
    const definitions = within(region).getAllByRole('definition')
    await act(async () => {
      await i18n.changeLanguage('de')
    })
    expect(screen.getByRole('region', { name: 'Administrationsübersicht' })).toBe(region)
    expect(within(region).getAllByRole('definition')).toEqual(definitions)
    expect(within(region).getAllByText('Nicht verfügbar')).toHaveLength(adminEventsEnabled ? 6 : 4)
  })
})
