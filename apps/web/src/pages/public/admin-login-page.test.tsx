import { fireEvent, render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import App from '@/App'
import i18n from '@/i18n'

function renderAdminLoginRoute() {
  return render(
    <MemoryRouter initialEntries={['/adminLogin']}>
      <App />
    </MemoryRouter>,
  )
}

describe('AdminLoginPage', () => {
  beforeEach(async () => {
    await i18n.changeLanguage('en')
  })

  it('renders a visually distinct accessible Admin Login surface at the direct URL', () => {
    const { container } = renderAdminLoginRoute()

    expect(screen.getByRole('heading', { level: 1, name: 'Administration access' })).toBeVisible()
    expect(screen.getByText('Restricted area')).toBeVisible()
    expect(container.querySelector('[data-auth-surface="admin"]')).toBeInTheDocument()
    expect(screen.getByLabelText('Admin email address')).toHaveAttribute('autocomplete', 'username')
    expect(screen.getByLabelText('Admin password')).toHaveAttribute(
      'autocomplete',
      'current-password',
    )
  })

  it('does not expose registration, User Login, or another Admin Login discovery link', () => {
    renderAdminLoginRoute()

    expect(document.querySelector('a[href="/register"]')).not.toBeInTheDocument()
    expect(document.querySelector('a[href="/login"]')).not.toBeInTheDocument()
    expect(document.querySelector('a[href="/adminLogin"]')).not.toBeInTheDocument()
    expect(document.querySelector('[name="role"]')).not.toBeInTheDocument()
  })

  it('validates required credentials and focuses the first invalid field', () => {
    renderAdminLoginRoute()

    fireEvent.click(screen.getByRole('button', { name: 'Continue to administration' }))

    expect(screen.getByText('Enter the administrator email address.')).toBeVisible()
    expect(screen.getByText('Enter the administrator password.')).toBeVisible()
    expect(screen.getByLabelText('Admin email address')).toHaveFocus()
  })

  it('rejects an invalid administrator email address', () => {
    renderAdminLoginRoute()

    fireEvent.change(screen.getByLabelText('Admin email address'), {
      target: { value: 'not-an-email' },
    })
    fireEvent.change(screen.getByLabelText('Admin password'), { target: { value: 'secret' } })
    fireEvent.click(screen.getByRole('button', { name: 'Continue to administration' }))

    expect(screen.getByText('Enter a valid administrator email address.')).toBeVisible()
    expect(screen.queryByRole('status')).not.toBeInTheDocument()
  })

  it('does not call an API or simulate Admin authentication on valid UI-only submit', () => {
    const fetch = vi.spyOn(globalThis, 'fetch')
    renderAdminLoginRoute()

    fireEvent.change(screen.getByLabelText('Admin email address'), {
      target: { value: 'admin@vgu.edu.vn' },
    })
    fireEvent.change(screen.getByLabelText('Admin password'), { target: { value: 'secret' } })
    fireEvent.click(screen.getByRole('button', { name: 'Continue to administration' }))

    expect(screen.getByRole('status')).toHaveTextContent(
      'Admin authentication will be connected when the authentication backend is available.',
    )
    expect(screen.getByRole('heading', { name: 'Administration access' })).toBeVisible()
    expect(fetch).not.toHaveBeenCalled()
    fetch.mockRestore()
  })

  it('renders the Admin Login surface in German', async () => {
    await i18n.changeLanguage('de')
    renderAdminLoginRoute()

    expect(screen.getByRole('heading', { level: 1, name: 'Verwaltungszugang' })).toBeVisible()
    expect(screen.getByText('Geschützter Bereich')).toBeVisible()
    expect(screen.getByLabelText('Admin-E-Mail-Adresse')).toBeVisible()
    expect(screen.getByLabelText('Admin-Passwort')).toBeVisible()
    expect(screen.getByRole('button', { name: 'Zur Verwaltung fortfahren' })).toBeVisible()
  })
})
