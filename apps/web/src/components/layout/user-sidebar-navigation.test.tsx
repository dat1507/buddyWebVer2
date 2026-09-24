import { act, fireEvent, render, screen, within } from '@testing-library/react'
import { MemoryRouter, Route, Routes, useLocation } from 'react-router'
import { beforeEach, describe, expect, it } from 'vitest'

import { UserSidebarNavigation } from '@/components/layout/user-sidebar-navigation'
import i18n from '@/i18n'
import { userNavigationItems, type UserNavigationItem } from '@/routes/user-navigation'

const locales = [
  [
    'en',
    'Student navigation',
    ['Edit Profile', 'My Profile', 'Buddy Matching', 'My Buddy', 'Events', 'Settings'],
  ],
  [
    'de',
    'Studierendennavigation',
    [
      'Profil bearbeiten',
      'Mein Profil',
      'Buddy-Matching',
      'Mein Buddy',
      'Veranstaltungen',
      'Einstellungen',
    ],
  ],
] as const

// Component inputs for released-page behavior beyond the production profile pages.
const releasedItems: readonly UserNavigationItem[] = userNavigationItems.map((item) =>
  item.to && ['editProfile', 'myProfile', 'events'].includes(item.id)
    ? { ...item, available: true, to: item.to }
    : item,
)

function LocationProbe() {
  const location = useLocation()
  return <p data-testid="location">{location.pathname + location.search + location.hash}</p>
}

function renderNavigation(path = '/user/profile/edit', items = userNavigationItems) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <UserSidebarNavigation items={items} />
      <LocationProbe />
      <Routes>
        <Route path="/user/profile/edit" element={<h1>Fixture editor</h1>} />
        <Route path="/user/profile" element={<h1>Fixture profile</h1>} />
        <Route path="/user/events" element={<h1>Fixture events</h1>} />
        <Route path="/user/events/:id" element={<h1>Fixture event detail</h1>} />
        <Route path="*" element={<h1>Fixture nested route</h1>} />
      </Routes>
    </MemoryRouter>,
  )
}

describe('FE-022 student sidebar navigation', () => {
  beforeEach(async () => {
    await i18n.changeLanguage('en')
  })

  it.each(locales)(
    'renders the scoped labels with unavailable semantics in %s',
    async (language, navLabel, labels) => {
      await i18n.changeLanguage(language)
      renderNavigation()
      const nav = screen.getByRole('navigation', { name: navLabel })
      const links = within(nav).getAllByRole('link')
      expect(links).toHaveLength(6)
      labels.forEach((label) => expect(within(nav).getByText(label)).toBeVisible())
      const profile = within(nav).getByRole('link', { name: i18n.t('userNavigation.myProfile') })
      expect(profile).toHaveAttribute('href', '/user/profile')
      expect(profile).not.toHaveAttribute('aria-disabled')
      const editProfile = within(nav).getByRole('link', {
        name: i18n.t('userNavigation.editProfile'),
      })
      expect(editProfile).toHaveAttribute('href', '/user/profile/edit')
      expect(editProfile).not.toHaveAttribute('aria-disabled')
      expect(editProfile).toHaveAttribute('aria-current', 'page')
      const settings = within(nav).getByRole('link', {
        name: i18n.t('userNavigation.settings'),
      })
      expect(settings).toHaveAttribute('href', '/user/settings')
      expect(settings).not.toHaveAttribute('aria-disabled')
      links
        .filter((link) => link !== profile && link !== editProfile && link !== settings)
        .forEach((link) => {
          expect(link).toHaveAttribute('aria-disabled', 'true')
          expect(link).not.toHaveAttribute('href')
          expect(link).not.toHaveAttribute('tabindex')
          expect(link).toHaveAccessibleDescription(i18n.t('userNavigation.unavailableHint'))
        })
      expect(nav.querySelectorAll('a')).toHaveLength(3)
      expect(nav).not.toHaveTextContent(/Dashboard|Übersicht/)
      expect(nav).not.toHaveTextContent(/Calendar|Notifications|Admin|Campus|AI assistant/)
      expect(screen.getByRole('heading', { name: 'Fixture editor' })).toBeVisible()
    },
  )

  it.each([
    ['/user/matching/preview', 'Buddy Matching'],
    ['/user/buddy/details', 'My Buddy'],
    ['/user/events/example', 'Events'],
  ])('marks the current route %s without enabling an unfinished destination', (path, label) => {
    renderNavigation(path)
    const nav = screen.getByRole('navigation')
    const current = nav.querySelector('[aria-current="page"]')
    expect(current).toHaveTextContent(label)
    expect(nav.querySelectorAll('[aria-current="page"]')).toHaveLength(1)
    expect(current).toHaveAttribute('aria-disabled', 'true')
    expect(current).not.toHaveAttribute('href')
  })

  it('keeps the released Settings link active on nested paths', () => {
    renderNavigation('/user/settings/session')
    const settings = screen.getByRole('link', { name: 'Settings' })
    expect(settings).toHaveAttribute('href', '/user/settings')
    expect(settings).toHaveAttribute('aria-current', 'page')
    expect(settings).not.toHaveAttribute('aria-disabled')
  })

  it('puts Edit Profile first and omits the retired Dashboard item', () => {
    renderNavigation('/user/profile/edit?source=test#content')
    const nav = screen.getByRole('navigation')
    expect(within(nav).getAllByRole('link')[0]).toHaveTextContent('Edit Profile')
    expect(within(nav).queryByText('Dashboard')).not.toBeInTheDocument()
  })

  it('exposes the released profile page as the current native link', () => {
    renderNavigation('/user/profile?view=details#photo')
    const profile = screen.getByRole('link', { name: 'My Profile' })
    expect(profile).toHaveAttribute('href', '/user/profile')
    expect(profile).toHaveAttribute('aria-current', 'page')
    expect(profile).not.toHaveAttribute('aria-disabled')
  })

  it('exposes profile editing as a released native link', () => {
    renderNavigation('/user/profile/edit')
    const editProfile = screen.getByRole('link', { name: 'Edit Profile' })
    expect(editProfile).toHaveAttribute('href', '/user/profile/edit')
    expect(editProfile).toHaveAttribute('aria-current', 'page')
    expect(editProfile).not.toHaveAttribute('aria-disabled')
  })

  it.each(['en', 'de'] as const)(
    'allows native links to supplied released pages and updates active state in %s',
    async (language) => {
      await i18n.changeLanguage(language)
      renderNavigation('/user/profile/edit', releasedItems)
      const nav = screen.getByRole('navigation')
      const editProfile = within(nav).getByRole('link', {
        name: i18n.t('userNavigation.editProfile'),
      })
      expect(editProfile).toHaveAttribute('aria-current', 'page')
      const profile = within(nav).getByRole('link', { name: i18n.t('userNavigation.myProfile') })
      expect(profile).toHaveAttribute('href', '/user/profile')
      profile.focus()
      expect(profile).toHaveFocus()
      fireEvent.click(profile)
      expect(screen.getByRole('heading', { name: 'Fixture profile' })).toBeVisible()
      expect(profile).toHaveAttribute('aria-current', 'page')
      expect(editProfile).not.toHaveAttribute('aria-current')
      fireEvent.click(within(nav).getByRole('link', { name: i18n.t('userNavigation.events') }))
      expect(screen.getByRole('heading', { name: 'Fixture events' })).toBeVisible()
      expect(screen.getByTestId('location').textContent).toBe('/user/events')
      expect(nav.querySelectorAll('a')).toHaveLength(4)
    },
  )

  it('keeps Events active on a nested route and respects segment boundaries', () => {
    const view = renderNavigation('/user/events/example?view=recap#photos', releasedItems)
    expect(screen.getByRole('link', { name: 'Events' })).toHaveAttribute('aria-current', 'page')
    expect(screen.getByRole('heading', { name: 'Fixture event detail' })).toBeVisible()
    view.unmount()
    renderNavigation('/user/events-other', releasedItems)
    expect(screen.getByRole('link', { name: 'Events' })).not.toHaveAttribute('aria-current')
  })

  it('does not let an unavailable item receive focus or change the route', () => {
    renderNavigation('/user/profile/edit', releasedItems)
    const editProfile = screen.getByRole('link', { name: 'Edit Profile' })
    editProfile.focus()
    const matching = screen.getByRole('link', { name: /Buddy Matching/ })
    matching.focus()
    expect(editProfile).toHaveFocus()
    fireEvent.click(matching)
    expect(screen.getByTestId('location').textContent).toBe('/user/profile/edit')
    expect(matching).toHaveAttribute('aria-disabled', 'true')
    expect(matching).not.toHaveAttribute('href')
    expect(matching).not.toHaveAttribute('aria-current')
  })

  it('updates navigation labels and descriptions without replacing the current item', async () => {
    renderNavigation('/user/profile')
    const current = screen.getByRole('navigation').querySelector('[aria-current="page"]')
    await act(async () => {
      await i18n.changeLanguage('de')
    })
    const nav = screen.getByRole('navigation', { name: 'Studierendennavigation' })
    expect(nav.querySelector('[aria-current="page"]')).toBe(current)
    expect(current).toHaveTextContent('Mein Profil')
    expect(current).toHaveAttribute('href', '/user/profile')
    expect(current).not.toHaveAccessibleDescription('Diese Seiten sind noch nicht verfügbar.')
    expect(screen.getByTestId('location').textContent).toBe('/user/profile')
  })
})
