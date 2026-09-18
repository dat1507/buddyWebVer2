import { fireEvent, render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import App from '@/App'
import i18n from '@/i18n'
import { sessionClient } from '@/features/auth/session-client'
import { useAuthStore } from '@/stores/auth-store'

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
    useAuthStore.getState().resetSession()
  })
  afterEach(() => {
    vi.restoreAllMocks()
    useAuthStore.getState().resetSession()
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

  it('requires ADMIN through the shared client and routes verified identity to administration', async () => {
    const admin = {
      id: 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa',
      email: 'admin@vgu.edu.vn',
      role: 'ADMIN' as const,
      email_verified: false,
    }
    const login = vi.spyOn(sessionClient, 'login').mockImplementation(async () => {
      useAuthStore.getState().setAuthenticated(admin)
      return admin
    })
    renderAdminLoginRoute()
    const password = screen.getByLabelText('Admin password')

    fireEvent.change(screen.getByLabelText('Admin email address'), {
      target: { value: 'admin@vgu.edu.vn' },
    })
    fireEvent.change(screen.getByLabelText('Admin password'), { target: { value: 'secret' } })
    fireEvent.click(screen.getByRole('button', { name: 'Continue to administration' }))

    expect(await screen.findByText('Admin overview')).toBeVisible()
    expect(login).toHaveBeenCalledWith(
      { email: 'admin@vgu.edu.vn', password: 'secret' },
      { requiredRole: 'ADMIN' },
    )
    expect(password).toHaveValue('')
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
