import { act, render, screen, within } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router'
import { beforeEach, describe, expect, it } from 'vitest'

import { AdminLayout } from '@/components/layout/admin-layout'
import { UserLayout } from '@/components/layout/user-layout'
import i18n from '@/i18n'
import { RoutePlaceholder } from '@/pages/route-placeholder'

const locales = [
  ['en', 'Student workspace', 'Student content', 'Skip to content'],
  ['de', 'Studierendenbereich', 'Inhalte des Studierendenbereichs', 'Zum Inhalt springen'],
] as const

describe('FE-021 UserLayout shell', () => {
  beforeEach(async () => {
    await i18n.changeLanguage('en')
  })

  it.each(locales)(
    'renders sidebar, one main and its nested route in %s',
    async (language, sidebarLabel, contentLabel, skipLabel) => {
      await i18n.changeLanguage(language)
      render(
        <MemoryRouter initialEntries={['/user/profile']}>
          <Routes>
            <Route path="user" element={<UserLayout />}>
              <Route path="profile" element={<RoutePlaceholder area="User" title="Profile" />} />
            </Route>
          </Routes>
        </MemoryRouter>,
      )

      expect(screen.getByRole('complementary', { name: sidebarLabel })).toBeVisible()
      const main = screen.getByRole('main', { name: contentLabel })
      expect(within(main).getByRole('heading', { name: 'Profile' })).toBeVisible()
      expect(screen.getAllByRole('main')).toHaveLength(1)
      expect(main.querySelector('main')).toBeNull()

      const skip = screen.getByRole('link', { name: skipLabel })
      expect(skip).toHaveAttribute('href', `#${main.id}`)
      expect(main).toHaveAttribute('tabindex', '-1')
      expect(document.getElementById(main.id)).toBe(main)
    },
  )

  it('updates visible and accessible labels when the language changes without remounting', async () => {
    render(
      <MemoryRouter>
        <Routes>
          <Route element={<UserLayout />}>
            <Route index element={<h1>Nested content</h1>} />
          </Route>
        </Routes>
      </MemoryRouter>,
    )
    const main = screen.getByRole('main', { name: 'Student content' })
    await act(async () => {
      await i18n.changeLanguage('de')
    })
    expect(screen.getByRole('main', { name: 'Inhalte des Studierendenbereichs' })).toBe(main)
    expect(screen.getByRole('complementary', { name: 'Studierendenbereich' })).toBeVisible()
    expect(within(main).getByRole('heading', { name: 'Nested content' })).toBeVisible()
  })

  it.each(['Public', 'Admin'] as const)('preserves one main landmark for a %s route', (area) => {
    render(
      <MemoryRouter>
        <Routes>
          <Route element={area === 'Admin' ? <AdminLayout /> : undefined}>
            <Route index element={<RoutePlaceholder area={area} title="Existing page" />} />
          </Route>
        </Routes>
      </MemoryRouter>,
    )
    expect(screen.getAllByRole('main')).toHaveLength(1)
    expect(
      within(screen.getByRole('main')).getByRole('heading', { name: 'Existing page' }),
    ).toBeVisible()
    if (area === 'Admin') {
      expect(screen.getByRole('complementary', { name: 'Administrator workspace' })).toBeVisible()
    } else {
      expect(screen.queryByRole('complementary')).not.toBeInTheDocument()
    }
  })
})
