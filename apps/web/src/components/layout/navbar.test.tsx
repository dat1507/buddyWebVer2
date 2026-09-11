import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { MemoryRouter } from 'react-router'
import { beforeEach, describe, expect, it } from 'vitest'

import { Navbar } from '@/components/layout/navbar'
import i18n from '@/i18n'

function renderNavbar() {
  return render(
    <MemoryRouter>
      <Navbar />
    </MemoryRouter>,
  )
}

describe('Navbar', () => {
  beforeEach(async () => {
    localStorage.clear()
    await i18n.changeLanguage('en')
  })

  it('renders primary navigation items and language toggle', () => {
    renderNavbar()

    expect(screen.getByRole('link', { name: 'Home' })).toBeVisible()
    expect(screen.getByRole('link', { name: 'About' })).toBeVisible()
    expect(screen.getByRole('link', { name: 'Features' })).toBeVisible()
    expect(screen.getByRole('link', { name: 'Community' })).toBeVisible()
    expect(screen.getByRole('link', { name: 'Contact' })).toBeVisible()

    const toggleBtns = screen.getAllByRole('button', { name: /Current language: EN/i })
    expect(toggleBtns.length).toBeGreaterThanOrEqual(1)
    expect(toggleBtns[0]).toBeVisible()
  })

  it('switches navigation labels when language toggle is clicked', async () => {
    renderNavbar()

    const toggleBtns = screen.getAllByRole('button', { name: /Current language: EN/i })
    fireEvent.click(toggleBtns[0])

    expect(i18n.resolvedLanguage).toBe('de')
    expect(screen.getByRole('link', { name: 'Startseite' })).toBeVisible()
    expect(screen.getByRole('link', { name: 'Über uns' })).toBeVisible()
    expect(screen.getByRole('link', { name: 'Funktionen' })).toBeVisible()
  })

  it('toggles language from mobile drawer and closes drawer', async () => {
    renderNavbar()

    // Open mobile menu
    const menuBtn = screen.getByRole('button', { name: 'Open navigation menu' })
    const navbarContent = menuBtn.closest('header')?.firstElementChild
    fireEvent.click(menuBtn)

    // Verify drawer dialog is open
    const dialog = screen.getByRole('dialog', { name: 'Primary navigation' })
    expect(dialog).toBeVisible()
    expect(navbarContent).toHaveAttribute('aria-hidden', 'true')
    expect(navbarContent).toHaveAttribute('inert')

    // Find and click mobile language toggle inside drawer
    const mobileToggle = within(dialog).getByRole('button', {
      name: 'Current language: EN. Switch to German',
    })
    fireEvent.click(mobileToggle)

    expect(i18n.resolvedLanguage).toBe('de')
    expect(localStorage.getItem('vgu-language')).toBe('de')

    // Verify drawer closed
    await waitFor(() => {
      expect(screen.queryByRole('dialog')).toBeNull()
    })
    expect(navbarContent).not.toHaveAttribute('aria-hidden')
    expect(navbarContent).not.toHaveAttribute('inert')
  })

  it('opens a desktop Sign in menu with User actions only', () => {
    renderNavbar()

    const trigger = screen.getByRole('button', { name: 'Sign in' })
    expect(trigger).toHaveAttribute('aria-expanded', 'false')
    expect(screen.queryByRole('navigation', { name: 'Account navigation' })).toBeNull()

    fireEvent.click(trigger)

    const accountNavigation = screen.getByRole('navigation', { name: 'Account navigation' })
    expect(trigger).toHaveAttribute('aria-expanded', 'true')
    expect(within(accountNavigation).getByRole('link', { name: 'User login' })).toHaveAttribute(
      'href',
      '/login',
    )
    expect(
      within(accountNavigation).getByRole('link', { name: 'Create student account' }),
    ).toHaveAttribute('href', '/register')
    expect(accountNavigation.querySelector('a[href="/adminLogin"]')).not.toBeInTheDocument()
  })

  it('closes the desktop Sign in menu with Escape and returns focus to its trigger', () => {
    renderNavbar()

    const trigger = screen.getByRole('button', { name: 'Sign in' })
    fireEvent.click(trigger)
    screen.getByRole('link', { name: 'User login' }).focus()
    fireEvent.keyDown(document, { key: 'Escape' })

    expect(screen.queryByRole('navigation', { name: 'Account navigation' })).toBeNull()
    expect(trigger).toHaveAttribute('aria-expanded', 'false')
    expect(trigger).toHaveFocus()
  })

  it('closes the desktop Sign in menu after an outside click', () => {
    renderNavbar()

    fireEvent.click(screen.getByRole('button', { name: 'Sign in' }))
    expect(screen.getByRole('navigation', { name: 'Account navigation' })).toBeVisible()

    fireEvent.mouseDown(document.body)

    expect(screen.queryByRole('navigation', { name: 'Account navigation' })).toBeNull()
  })

  it('localizes the desktop Sign in menu in German', async () => {
    await i18n.changeLanguage('de')
    renderNavbar()

    fireEvent.click(screen.getByRole('button', { name: 'Anmelden' }))

    const accountNavigation = screen.getByRole('navigation', { name: 'Kontonavigation' })
    expect(
      within(accountNavigation).getByRole('link', { name: 'Benutzeranmeldung' }),
    ).toHaveAttribute('href', '/login')
    expect(
      within(accountNavigation).getByRole('link', { name: 'Studierendenkonto erstellen' }),
    ).toHaveAttribute('href', '/register')
  })

  it('exposes direct User auth actions in the mobile drawer and no Admin Login link', async () => {
    renderNavbar()

    fireEvent.click(screen.getByRole('button', { name: 'Open navigation menu' }))
    const dialog = screen.getByRole('dialog', { name: 'Primary navigation' })
    const userLogin = within(dialog).getByRole('link', { name: 'User login' })

    expect(userLogin).toHaveAttribute('href', '/login')
    expect(within(dialog).getByRole('link', { name: 'Create student account' })).toHaveAttribute(
      'href',
      '/register',
    )
    expect(dialog.querySelector('a[href="/adminLogin"]')).not.toBeInTheDocument()

    fireEvent.click(userLogin)

    await waitFor(() => {
      expect(screen.queryByRole('dialog')).toBeNull()
    })
  })

  it('localizes the direct mobile auth actions in German', async () => {
    await i18n.changeLanguage('de')
    renderNavbar()

    fireEvent.click(screen.getByRole('button', { name: 'Navigationsmenü öffnen' }))
    const dialog = screen.getByRole('dialog', { name: 'Hauptnavigation' })

    expect(within(dialog).getByRole('link', { name: 'Benutzeranmeldung' })).toHaveAttribute(
      'href',
      '/login',
    )
    expect(
      within(dialog).getByRole('link', { name: 'Studierendenkonto erstellen' }),
    ).toHaveAttribute('href', '/register')
  })
})
