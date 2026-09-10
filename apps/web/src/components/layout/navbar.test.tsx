import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { beforeEach, describe, expect, it } from 'vitest'

import { Navbar } from '@/components/layout/navbar'
import i18n from '@/i18n'

describe('Navbar with LanguageToggle (FE-020)', () => {
  beforeEach(async () => {
    localStorage.clear()
    await i18n.changeLanguage('en')
  })

  it('renders primary navigation items and language toggle', () => {
    render(<Navbar />)

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
    render(<Navbar />)

    const toggleBtns = screen.getAllByRole('button', { name: /Current language: EN/i })
    fireEvent.click(toggleBtns[0])

    expect(i18n.resolvedLanguage).toBe('de')
    expect(screen.getByRole('link', { name: 'Startseite' })).toBeVisible()
    expect(screen.getByRole('link', { name: 'Über uns' })).toBeVisible()
    expect(screen.getByRole('link', { name: 'Funktionen' })).toBeVisible()
  })

  it('toggles language from mobile drawer and closes drawer', async () => {
    render(<Navbar />)

    // Open mobile menu
    const menuBtn = screen.getByRole('button', { name: 'Open navigation menu' })
    fireEvent.click(menuBtn)

    // Verify drawer dialog is open
    const dialog = screen.getByRole('dialog', { name: 'Primary navigation' })
    expect(dialog).toBeVisible()

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
  })
})
