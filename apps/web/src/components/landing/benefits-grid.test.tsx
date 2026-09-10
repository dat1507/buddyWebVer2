import { render, screen } from '@testing-library/react'
import { beforeEach, describe, expect, it } from 'vitest'

import { BenefitsGrid } from '@/components/landing/benefits-grid'
import i18n from '@/i18n'

describe('BenefitsGrid', () => {
  beforeEach(async () => {
    await i18n.changeLanguage('en')
  })

  it('renders exactly 6 benefit cards', () => {
    render(<BenefitsGrid />)

    expect(screen.getByRole('heading', { name: 'Merchandise' })).toBeVisible()
    expect(screen.getByRole('heading', { name: 'Events Calendar' })).toBeVisible()
    expect(screen.getByRole('heading', { name: 'Library Regulations' })).toBeVisible()
    expect(screen.getByRole('heading', { name: 'Sports Hall' })).toBeVisible()
    expect(screen.getByRole('heading', { name: 'International Office' })).toBeVisible()
    expect(screen.getByRole('heading', { name: 'Dormitory Service' })).toBeVisible()
  })

  it('renders section title and subtitle', () => {
    render(<BenefitsGrid />)

    expect(screen.getByRole('heading', { name: 'Outstanding Benefits' })).toBeVisible()
    expect(
      screen.getByText(
        'Everything you need for an amazing university experience, all in one platform.',
      ),
    ).toBeVisible()
  })

  it('renders bullet items for each card', () => {
    render(<BenefitsGrid />)

    // Check a few representative bullet items across different cards
    expect(screen.getByText('Show it')).toBeVisible()
    expect(screen.getByText('Stay updated')).toBeVisible()
    expect(screen.getByText('Play hard')).toBeVisible()
    expect(screen.getByText('Cozy living')).toBeVisible()
  })

  it('does not render any links or buttons inside the grid', () => {
    const { container } = render(<BenefitsGrid />)

    const section = container.querySelector('#features')!
    const links = section.querySelectorAll('a')
    const buttons = section.querySelectorAll('button')

    expect(links).toHaveLength(0)
    expect(buttons).toHaveLength(0)
  })

  it('uses German content after a language change', async () => {
    await i18n.changeLanguage('de')
    render(<BenefitsGrid />)

    expect(screen.getByRole('heading', { name: 'Hervorragende Vorteile' })).toBeVisible()
    expect(screen.getByRole('heading', { name: 'Merchandise' })).toBeVisible()
    expect(screen.getByRole('heading', { name: 'Eventkalender' })).toBeVisible()
    expect(screen.getByRole('heading', { name: 'Bibliotheksregeln' })).toBeVisible()
    expect(screen.getByRole('heading', { name: 'Sporthalle' })).toBeVisible()
    expect(screen.getByRole('heading', { name: 'International Office' })).toBeVisible()
    expect(screen.getByRole('heading', { name: 'Wohnheimservice' })).toBeVisible()
  })
})
