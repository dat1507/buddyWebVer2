import { fireEvent, render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import App from '@/App'
import i18n from '@/i18n'

function renderLoginRoute() {
  return render(
    <MemoryRouter initialEntries={['/login']}>
      <App />
    </MemoryRouter>,
  )
}

describe('UserLoginPage', () => {
  beforeEach(async () => {
    await i18n.changeLanguage('en')
  })

  it('renders the real /login route with an accessible user form', () => {
    renderLoginRoute()

    expect(screen.getByRole('heading', { level: 1, name: 'Welcome back' })).toBeVisible()
    expect(screen.getByLabelText('Email address')).toHaveAttribute('autocomplete', 'email')
    expect(screen.getByLabelText('Password')).toHaveAttribute('autocomplete', 'current-password')
    expect(screen.getByRole('button', { name: 'Sign in' })).toBeEnabled()
    expect(screen.getByRole('link', { name: 'Create an account' })).toHaveAttribute(
      'href',
      '/register',
    )
    expect(screen.queryByRole('link', { name: /admin/i })).not.toBeInTheDocument()
    expect(document.querySelector('a[href="/adminLogin"]')).not.toBeInTheDocument()
  })

  it('validates required fields and focuses the first invalid input', () => {
    renderLoginRoute()

    fireEvent.click(screen.getByRole('button', { name: 'Sign in' }))

    expect(screen.getByText('Enter your email address.')).toBeVisible()
    expect(screen.getByText('Enter your password.')).toBeVisible()
    expect(screen.getByLabelText('Email address')).toHaveAttribute('aria-invalid', 'true')
    expect(screen.getByLabelText('Email address')).toHaveFocus()
  })

  it('rejects an invalid email address without submitting authentication', () => {
    renderLoginRoute()

    fireEvent.change(screen.getByLabelText('Email address'), {
      target: { value: 'not-an-email' },
    })
    fireEvent.change(screen.getByLabelText('Password'), { target: { value: 'secret' } })
    fireEvent.click(screen.getByRole('button', { name: 'Sign in' }))

    expect(screen.getByText('Enter a valid email address.')).toBeVisible()
    expect(screen.queryByRole('status')).not.toBeInTheDocument()
  })

  it('keeps a valid UI-only submission on /login without calling an API', () => {
    const fetch = vi.spyOn(globalThis, 'fetch')
    renderLoginRoute()

    fireEvent.change(screen.getByLabelText('Email address'), {
      target: { value: 'student@example.com' },
    })
    fireEvent.change(screen.getByLabelText('Password'), { target: { value: 'secret' } })
    fireEvent.click(screen.getByRole('button', { name: 'Sign in' }))

    expect(screen.getByRole('status')).toHaveTextContent(
      'Sign-in will be connected when the authentication backend is available.',
    )
    expect(screen.getByRole('heading', { name: 'Welcome back' })).toBeVisible()
    expect(fetch).not.toHaveBeenCalled()
    fetch.mockRestore()
  })

  it('renders the login form in German', async () => {
    await i18n.changeLanguage('de')
    renderLoginRoute()

    expect(screen.getByRole('heading', { level: 1, name: 'Willkommen zurück' })).toBeVisible()
    expect(screen.getByLabelText('E-Mail-Adresse')).toBeVisible()
    expect(screen.getByLabelText('Passwort')).toBeVisible()
    expect(screen.getByRole('button', { name: 'Anmelden' })).toBeVisible()
    expect(screen.getByRole('link', { name: 'Konto erstellen' })).toHaveAttribute(
      'href',
      '/register',
    )
  })
})
