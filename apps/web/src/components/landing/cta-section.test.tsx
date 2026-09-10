import { fireEvent, render, screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { CtaSection } from '@/components/landing/cta-section'
import i18n from '@/i18n'

describe('CtaSection', () => {
  beforeEach(async () => {
    await i18n.changeLanguage('en')
  })

  it('renders section title and subtitle', () => {
    render(<CtaSection />)

    expect(
      screen.getByRole('heading', { name: 'Ready to Transform Your University Experience?' }),
    ).toBeVisible()
    expect(
      screen.getByText(
        'Join thousands of VGU students who are already making the most of their university journey.',
      ),
    ).toBeVisible()
  })

  it('renders Join and Demo buttons with correct accessible roles', () => {
    render(<CtaSection />)

    const joinBtn = screen.getByRole('button', { name: 'Join the Community' })
    const demoBtn = screen.getByRole('button', { name: 'Watch Demo' })

    expect(joinBtn).toBeVisible()
    expect(joinBtn).toBeEnabled()

    expect(demoBtn).toBeVisible()
    expect(demoBtn).toBeEnabled()
  })

  it('renders German content after language switch', async () => {
    await i18n.changeLanguage('de')
    render(<CtaSection />)

    expect(
      screen.getByRole('heading', { name: 'Bereit, dein Unileben zu transformieren?' }),
    ).toBeVisible()
    expect(
      screen.getByText(
        'Schließe dich tausenden VGU-Studierenden an, die bereits das Beste aus ihrem Studium machen.',
      ),
    ).toBeVisible()
    expect(screen.getByRole('button', { name: 'Community beitreten' })).toBeVisible()
    expect(screen.getByRole('button', { name: 'Demo ansehen' })).toBeVisible()
  })

  it('buttons are keyboard focusable', () => {
    render(<CtaSection />)

    const joinBtn = screen.getByRole('button', { name: 'Join the Community' })
    const demoBtn = screen.getByRole('button', { name: 'Watch Demo' })

    joinBtn.focus()
    expect(document.activeElement).toBe(joinBtn)

    demoBtn.focus()
    expect(document.activeElement).toBe(demoBtn)
  })

  it('opens the demo dialog on demand and returns focus when it closes', () => {
    const pause = vi.spyOn(HTMLMediaElement.prototype, 'pause').mockImplementation(() => undefined)
    render(<CtaSection />)
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

  it('does not contain unverified links or external navigation', () => {
    const { container } = render(<CtaSection />)
    const section = container.querySelector('#cta')!

    expect(section.querySelectorAll('a')).toHaveLength(0)
  })
})
