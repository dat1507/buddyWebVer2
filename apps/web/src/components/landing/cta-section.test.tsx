import { fireEvent, render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router'
import { beforeEach, describe, expect, it, vi } from 'vitest'

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

  it('renders an internal registration link and the Demo button with correct roles', () => {
    renderCtaSection()

    const joinLink = screen.getByRole('link', { name: 'Join the Community' })
    const demoBtn = screen.getByRole('button', { name: 'Watch Demo' })

    expect(joinLink).toBeVisible()
    expect(joinLink).toHaveAttribute('href', '/register')

    expect(demoBtn).toBeVisible()
    expect(demoBtn).toBeEnabled()
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
    expect(screen.getByRole('button', { name: 'Demo ansehen' })).toBeVisible()
  })

  it('actions are keyboard focusable', () => {
    renderCtaSection()

    const joinLink = screen.getByRole('link', { name: 'Join the Community' })
    const demoBtn = screen.getByRole('button', { name: 'Watch Demo' })

    joinLink.focus()
    expect(document.activeElement).toBe(joinLink)

    demoBtn.focus()
    expect(document.activeElement).toBe(demoBtn)
  })

  it('opens the demo dialog on demand and returns focus when it closes', () => {
    const pause = vi.spyOn(HTMLMediaElement.prototype, 'pause').mockImplementation(() => undefined)
    renderCtaSection()
    const demoButton = screen.getByRole('button', { name: 'Watch Demo' })

    expect(document.querySelector('video')).not.toBeInTheDocument()
    expect(demoButton).toHaveAttribute('aria-expanded', 'false')

    demoButton.focus()
    fireEvent.click(demoButton)

    expect(screen.getByRole('dialog', { name: 'VGU Buddy Program Demo' })).toBeVisible()
    expect(screen.getByLabelText('VGU Buddy Program demo video')).toBeInTheDocument()
    expect(demoButton).toHaveAttribute('aria-expanded', 'true')

    fireEvent.click(screen.getByRole('button', { name: 'Close demo video' }))

    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
    expect(demoButton).toHaveAttribute('aria-expanded', 'false')
    expect(demoButton).toHaveFocus()
    pause.mockRestore()
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
