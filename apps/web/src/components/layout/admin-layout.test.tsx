import { act, fireEvent, render, screen, within } from '@testing-library/react'
import { Link, MemoryRouter, Route, Routes } from 'react-router'
import { beforeEach, describe, expect, it } from 'vitest'

import { AdminLayout } from '@/components/layout/admin-layout'
import i18n from '@/i18n'
import { RoutePlaceholder } from '@/pages/route-placeholder'

const locales = [
  ['en', 'Administrator workspace', 'Administrator content', 'Skip to content'],
  ['de', 'Administrationsbereich', 'Inhalte der Administration', 'Zum Inhalt springen'],
] as const

describe('ADMIN-001 AdminLayout shell', () => {
  beforeEach(async () => {
    await i18n.changeLanguage('en')
  })

  it.each(locales)(
    'renders its sidebar, Admin identity and one nested content main in %s',
    async (language, sidebarLabel, contentLabel, skipLabel) => {
      await i18n.changeLanguage(language)
      render(
        <MemoryRouter initialEntries={['/admin/users']}>
          <Routes>
            <Route path="admin" element={<AdminLayout />}>
              <Route
                path="users"
                element={<RoutePlaceholder area="Admin" title="User management" />}
              />
            </Route>
          </Routes>
        </MemoryRouter>,
      )
      const sidebar = screen.getByRole('complementary', { name: sidebarLabel })
      expect(within(sidebar).getByText('VGU Buddy')).toBeVisible()
      expect(within(sidebar).getByText('Admin')).toBeVisible()
      expect(within(sidebar).getByRole('button', { name: /EN|DE/ })).toBeVisible()
      expect(within(sidebar).queryByRole('navigation')).not.toBeInTheDocument()
      const main = screen.getByRole('main', { name: contentLabel })
      expect(within(main).getByRole('heading', { name: 'User management' })).toBeVisible()
      expect(screen.getAllByRole('main')).toHaveLength(1)
      expect(main.querySelector('main')).toBeNull()
      expect(main).toHaveAttribute('tabindex', '-1')
      expect(screen.getByRole('link', { name: skipLabel })).toHaveAttribute('href', `#${main.id}`)
    },
  )

  it('updates EN/DE landmarks without replacing the content or skip-link target', async () => {
    render(
      <MemoryRouter>
        <Routes>
          <Route element={<AdminLayout />}>
            <Route index element={<h1>Nested content</h1>} />
          </Route>
        </Routes>
      </MemoryRouter>,
    )
    const main = screen.getByRole('main', { name: 'Administrator content' })
    const skip = screen.getByRole('link', { name: 'Skip to content' })
    await act(async () => {
      await i18n.changeLanguage('de')
    })
    expect(screen.getByRole('main', { name: 'Inhalte der Administration' })).toBe(main)
    expect(screen.getByRole('link', { name: 'Zum Inhalt springen' })).toBe(skip)
    expect(skip).toHaveAttribute('href', `#${main.id}`)
    expect(within(main).getByRole('heading', { name: 'Nested content' })).toBeVisible()
    expect(screen.getByRole('complementary', { name: 'Administrationsbereich' })).toBeVisible()
  })

  it('keeps the shell and its content region mounted when a nested route changes', () => {
    render(
      <MemoryRouter initialEntries={['/admin/dashboard']}>
        <Routes>
          <Route path="admin" element={<AdminLayout />}>
            <Route
              path="dashboard"
              element={<Link to="/admin/users">Open nested users page</Link>}
            />
            <Route path="users" element={<h1>Nested users page</h1>} />
          </Route>
        </Routes>
      </MemoryRouter>,
    )
    const main = screen.getByRole('main', { name: 'Administrator content' })
    const sidebar = screen.getByRole('complementary', { name: 'Administrator workspace' })
    fireEvent.click(within(main).getByRole('link', { name: 'Open nested users page' }))
    expect(within(main).getByRole('heading', { name: 'Nested users page' })).toBeVisible()
    expect(screen.getByRole('main', { name: 'Administrator content' })).toBe(main)
    expect(screen.getByRole('complementary', { name: 'Administrator workspace' })).toBe(sidebar)
  })
})
