import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router'
import { beforeEach, describe, expect, it } from 'vitest'

import { CtaSection } from '@/components/landing/cta-section'
import i18n from '@/i18n'

function renderCtaSection() {
  return render(
    <MemoryRouter>
      <CtaSection />
    </MemoryRouter>,
  )
}

describe('CtaSection', () => {
  beforeEach(async () => {
    await i18n.changeLanguage('en')
  })

  it('renders section title and subtitle', () => {
    renderCtaSection()

    expect(
      screen.getByRole('heading', { name: 'Ready to Transform Your University Experience?' }),
    ).toBeVisible()
    expect(
      screen.getByText(
        'Join thousands of VGU students who are already making the most of their university journey.',
      ),
    ).toBeVisible()
  })

  it('renders one centered registration action without demo UI', () => {
    const { container } = renderCtaSection()

    const joinLink = screen.getByRole('link', { name: 'Join the Community' })
    const actions = joinLink.parentElement

    expect(joinLink).toBeVisible()
    expect(joinLink).toHaveAttribute('href', '/register')
    expect(joinLink).toHaveClass('w-full', 'sm:w-auto')
    expect(actions).toHaveClass('flex', 'justify-center')
    expect(actions).not.toHaveClass('gap-4', 'sm:gap-5')
    expect(screen.queryByRole('button', { name: 'Watch Demo' })).not.toBeInTheDocument()
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
    expect(container.querySelector('video')).not.toBeInTheDocument()
  })

  it('renders German content after language switch', async () => {
    await i18n.changeLanguage('de')
    renderCtaSection()

    expect(
      screen.getByRole('heading', { name: 'Bereit, dein Unileben zu transformieren?' }),
    ).toBeVisible()
    expect(
      screen.getByText(
        'Schließe dich tausenden VGU-Studierenden an, die bereits das Beste aus ihrem Studium machen.',
      ),
    ).toBeVisible()
    expect(screen.getByRole('link', { name: 'Community beitreten' })).toHaveAttribute(
      'href',
      '/register',
    )
    expect(screen.queryByRole('button', { name: 'Demo ansehen' })).not.toBeInTheDocument()
  })

  it('keeps the registration action keyboard focusable', () => {
    renderCtaSection()

    const joinLink = screen.getByRole('link', { name: 'Join the Community' })

    joinLink.focus()
    expect(document.activeElement).toBe(joinLink)
  })

  it('contains only the approved internal registration link', () => {
    const { container } = renderCtaSection()
    const section = container.querySelector('#cta')!
    const links = section.querySelectorAll('a')

    expect(links).toHaveLength(1)
    expect(links[0]).toHaveAttribute('href', '/register')
    expect(links[0]).not.toHaveAttribute('target')
    expect(section.querySelector('a[href="/adminLogin"]')).not.toBeInTheDocument()
  })
})
