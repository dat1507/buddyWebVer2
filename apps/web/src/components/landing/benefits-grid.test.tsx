import { render, screen, within } from '@testing-library/react'
import { beforeEach, describe, expect, it } from 'vitest'
import { BenefitsGrid } from '@/components/landing/benefits-grid'
import i18n from '@/i18n'

describe('Campus Resources', () => {
  beforeEach(async () => {
    await i18n.changeLanguage('en')
  })
  it('renders five resources with the preserved anchor and navbar clearance', () => {
    render(<BenefitsGrid />)
    const section = screen.getByRole('region', { name: 'Explore VGU Campus Resources' })
    expect(section).toHaveAttribute('id', 'features')
    expect(section).toHaveClass('scroll-mt-20')
    expect(within(section).getAllByRole('heading', { level: 3 })).toHaveLength(5)
    for (const name of [
      'Events Recap',
      'Library',
      'Sports Hall',
      'International Office',
      'Dormitory Service',
    ]) {
      expect(screen.getByRole('heading', { name })).toBeVisible()
    }
    expect(screen.queryByText('Merchandise')).not.toBeInTheDocument()
    expect(
      screen.getByText(
        'Discover the facilities, services, and opportunities that support student life at Vietnamese-German University.',
      ),
    ).toBeVisible()
  })
  it('opens the verified official resource securely with accessible keyboard focus', () => {
    render(<BenefitsGrid />)
    const link = screen.getByRole('link', {
      name: 'Visit International Office (opens in a new tab)',
    })
    expect(link).toHaveAttribute('href', 'https://vgu.edu.vn/international-office')
    expect(link).toHaveAttribute('target', '_blank')
    expect(link).toHaveAttribute('rel', 'noopener noreferrer')
    expect(link).toHaveClass('focus-visible:ring-2', 'min-h-11')
    link.focus()
    expect(link).toHaveFocus()
  })
  it('keeps recap informational and uses only confirmed destinations', () => {
    render(<BenefitsGrid />)
    expect(screen.getAllByRole('link')).toHaveLength(4)
    expect(screen.queryByRole('button')).not.toBeInTheDocument()
    expect(screen.getByText('Event highlights are being prepared.')).toBeVisible()
    expect(screen.getAllByRole('link').map((link) => link.getAttribute('href'))).toEqual([
      'https://library.vgu.edu.vn/',
      'https://vgu.edu.vn/sports-complex',
      'https://vgu.edu.vn/international-office',
      'https://dorm.vgu.edu.vn/',
    ])
  })
  it('renders German resources, link labels and pending states', async () => {
    await i18n.changeLanguage('de')
    render(<BenefitsGrid />)
    expect(
      screen.getByRole('region', { name: 'Entdecke die Campus-Angebote der VGU' }),
    ).toBeVisible()
    for (const name of [
      'Veranstaltungsrückblicke',
      'Bibliothek',
      'Sporthalle',
      'International Office',
      'Wohnheimservice',
    ]) {
      expect(screen.getByRole('heading', { name })).toBeVisible()
    }
    expect(
      screen.getByRole('link', {
        name: 'International Office besuchen (öffnet in einem neuen Tab)',
      }),
    ).toBeVisible()
    expect(screen.getByText('Veranstaltungsrückblicke werden vorbereitet.')).toBeVisible()
  })
})
