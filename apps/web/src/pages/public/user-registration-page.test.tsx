import { fireEvent, render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import App from '@/App'
import i18n from '@/i18n'

function renderRegistrationRoute() {
  return render(
    <MemoryRouter initialEntries={['/register']}>
      <App />
    </MemoryRouter>,
  )
}

describe('UserRegistrationPage', () => {
  beforeEach(async () => {
    await i18n.changeLanguage('en')
  })

  it('renders an accessible student registration form without an Admin path or role control', () => {
    renderRegistrationRoute()

    expect(screen.getByRole('heading', { level: 1, name: 'Create your account' })).toBeVisible()
    expect(screen.getByLabelText('Email address')).toHaveAttribute('autocomplete', 'email')
    expect(screen.getByLabelText('Password')).toHaveAttribute('autocomplete', 'new-password')
    expect(
      screen.getByRole('checkbox', {
        name: 'I consent to VGU Buddy processing my personal data to provide this service.',
      }),
    ).toBeRequired()
    expect(screen.getByRole('link', { name: 'Sign in' })).toHaveAttribute('href', '/login')
    expect(document.querySelector('[name="role"]')).not.toBeInTheDocument()
    expect(document.querySelector('a[href="/adminLogin"]')).not.toBeInTheDocument()
  })

  it('validates required fields and focuses the first invalid input', () => {
    renderRegistrationRoute()

    fireEvent.click(screen.getByRole('button', { name: 'Create student account' }))

    expect(screen.getByText('Enter your email address.')).toBeVisible()
    expect(screen.getByText('Enter a password.')).toBeVisible()
    expect(screen.getByText('Consent is required to create an account.')).toBeVisible()
    expect(screen.getByLabelText('Email address')).toHaveFocus()
  })

  it('rejects an invalid email address', () => {
    renderRegistrationRoute()

    fireEvent.change(screen.getByLabelText('Email address'), {
      target: { value: 'not-an-email' },
    })
    fireEvent.change(screen.getByLabelText('Password'), { target: { value: 'secret' } })
    fireEvent.click(screen.getByRole('checkbox'))
    fireEvent.click(screen.getByRole('button', { name: 'Create student account' }))

    expect(screen.getByText('Enter a valid email address.')).toBeVisible()
    expect(screen.queryByRole('status')).not.toBeInTheDocument()
  })

  it('requires explicit consent before accepting the UI-only form', () => {
    renderRegistrationRoute()

    fireEvent.change(screen.getByLabelText('Email address'), {
      target: { value: 'student@example.com' },
    })
    fireEvent.change(screen.getByLabelText('Password'), { target: { value: 'secret' } })
    fireEvent.click(screen.getByRole('button', { name: 'Create student account' }))

    expect(screen.getByText('Consent is required to create an account.')).toBeVisible()
    expect(screen.getByRole('checkbox')).toHaveFocus()
    expect(screen.queryByRole('status')).not.toBeInTheDocument()
  })

  it('does not call an API or simulate account creation after a valid UI-only submit', () => {
    const fetch = vi.spyOn(globalThis, 'fetch')
    renderRegistrationRoute()

    fireEvent.change(screen.getByLabelText('Email address'), {
      target: { value: 'student@example.com' },
    })
    fireEvent.change(screen.getByLabelText('Password'), { target: { value: 'secret' } })
    fireEvent.click(screen.getByRole('checkbox'))
    fireEvent.click(screen.getByRole('button', { name: 'Create student account' }))

    expect(screen.getByRole('status')).toHaveTextContent(
      'Account creation will be connected when the authentication backend is available.',
    )
    expect(screen.getByRole('heading', { name: 'Create your account' })).toBeVisible()
    expect(fetch).not.toHaveBeenCalled()
    fetch.mockRestore()
  })

  it('renders the registration form in German', async () => {
    await i18n.changeLanguage('de')
    renderRegistrationRoute()

    expect(screen.getByRole('heading', { level: 1, name: 'Konto erstellen' })).toBeVisible()
    expect(screen.getByLabelText('E-Mail-Adresse')).toBeVisible()
    expect(screen.getByLabelText('Passwort')).toBeVisible()
    expect(screen.getByRole('button', { name: 'Studierendenkonto erstellen' })).toBeVisible()
    expect(screen.getByRole('link', { name: 'Anmelden' })).toHaveAttribute('href', '/login')
  })
})
