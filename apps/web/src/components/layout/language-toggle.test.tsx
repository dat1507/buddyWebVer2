import { fireEvent, render, screen } from '@testing-library/react'
import { beforeEach, describe, expect, it } from 'vitest'

import { LanguageToggle, UkFlag } from '@/components/layout/language-toggle'
import i18n from '@/i18n'

describe('LanguageToggle (FE-020)', () => {
  beforeEach(async () => {
    localStorage.clear()
    await i18n.changeLanguage('en')
  })

  it('renders default English state with EN label and flag icon', () => {
    render(<LanguageToggle />)

    const button = screen.getByRole('button')
    expect(button).toBeVisible()
    expect(button).toHaveTextContent('EN')
    expect(button).toHaveAttribute('aria-label', 'Current language: EN. Switch to German')
    expect(button).toHaveAttribute('title', 'Switch to German')
  })

  it('renders multiple UK flags without duplicate SVG ids', () => {
    const { container } = render(
      <>
        <UkFlag />
        <UkFlag />
      </>,
    )

    expect(container.querySelectorAll('svg')).toHaveLength(2)
    expect(container.querySelectorAll('[id]')).toHaveLength(0)
    expect(container.querySelectorAll('clipPath')).toHaveLength(0)
  })

  it('toggles language from EN to DE on click and persists to localStorage', async () => {
    render(<LanguageToggle />)

    const button = screen.getByRole('button')
    fireEvent.click(button)

    // Await language transition
    expect(i18n.resolvedLanguage).toBe('de')
    expect(localStorage.getItem('vgu-language')).toBe('de')
    expect(button).toHaveTextContent('DE')
    expect(button).toHaveAttribute('aria-label', 'Aktuelle Sprache: DE. Zu Englisch wechseln')
    expect(button).toHaveAttribute('title', 'Zu Englisch wechseln')
  })

  it('toggles language from DE back to EN on second click', async () => {
    render(<LanguageToggle />)

    const button = screen.getByRole('button')

    // First click: EN -> DE
    fireEvent.click(button)
    expect(i18n.resolvedLanguage).toBe('de')

    // Second click: DE -> EN
    fireEvent.click(button)
    expect(i18n.resolvedLanguage).toBe('en')
    expect(localStorage.getItem('vgu-language')).toBe('en')
    expect(button).toHaveTextContent('EN')
  })

  it('renders mobile variant with interactive button and triggers toggle', async () => {
    render(<LanguageToggle variant="mobile" />)

    const button = screen.getByRole('button')
    expect(button).toBeVisible()
    expect(button).toHaveTextContent(/Language|Sprache/)
    expect(button).toHaveTextContent('EN')
    expect(button).toHaveAttribute('aria-label', 'Current language: EN. Switch to German')

    fireEvent.click(button)
    expect(i18n.resolvedLanguage).toBe('de')
    expect(localStorage.getItem('vgu-language')).toBe('de')
    expect(button).toHaveTextContent('DE')
    expect(button).toHaveAttribute('aria-label', 'Aktuelle Sprache: DE. Zu Englisch wechseln')
  })

  it('is accessible via keyboard focus and can be activated', () => {
    render(<LanguageToggle />)

    const button = screen.getByRole('button')
    button.focus()
    expect(document.activeElement).toBe(button)
  })
})
