import { QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen, within } from '@testing-library/react'
import { MemoryRouter } from 'react-router'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import App from '@/App'
import i18n from '@/i18n'
import { sessionClient } from '@/features/auth/session-client'
import { queryClient } from '@/lib/query-client'
import { useAuthStore } from '@/stores/auth-store'
import { completeProfileCompletion } from '@/test/profile-completion'
import { completeOwnProfile } from '@/test/profile'

function renderLoginRoute() {
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={['/login']}>
        <App />
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

describe('UserLoginPage', () => {
  beforeEach(async () => {
    await i18n.changeLanguage('en')
    useAuthStore.getState().resetSession()
    queryClient.setQueryData(['profile', 'own'], completeOwnProfile)
    queryClient.setQueryData(['profile', 'completion'], completeProfileCompletion)
  })
  afterEach(() => {
    vi.restoreAllMocks()
    queryClient.clear()
    useAuthStore.getState().resetSession()
  })

  it('renders the real /login route with an accessible user form', () => {
    renderLoginRoute()

    expect(screen.getByRole('heading', { level: 1, name: 'Welcome back' })).toBeVisible()
    expect(screen.getByLabelText('Email address')).toHaveAttribute('autocomplete', 'email')
    expect(screen.getByLabelText('Password')).toHaveAttribute('autocomplete', 'current-password')
    expect(within(screen.getByRole('main')).getByRole('button', { name: 'Sign in' })).toBeEnabled()
    expect(screen.getByRole('link', { name: 'Create an account' })).toHaveAttribute(
      'href',
      '/register',
    )
    expect(screen.queryByRole('link', { name: /admin/i })).not.toBeInTheDocument()
    expect(document.querySelector('a[href="/adminLogin"]')).not.toBeInTheDocument()
  })

  it('validates required fields and focuses the first invalid input', () => {
    renderLoginRoute()

    fireEvent.click(within(screen.getByRole('main')).getByRole('button', { name: 'Sign in' }))

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
    fireEvent.click(within(screen.getByRole('main')).getByRole('button', { name: 'Sign in' }))

    expect(screen.getByText('Enter a valid email address.')).toBeVisible()
    expect(screen.queryByRole('status')).not.toBeInTheDocument()
  })

  it('submits credentials and routes the verified session while clearing the password', async () => {
    const user = {
      id: 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa',
      email: 'student@example.com',
      role: 'USER' as const,
      email_verified: false,
    }
    const login = vi.spyOn(sessionClient, 'login').mockImplementation(async () => {
      useAuthStore.getState().setAuthenticated(user)
      return user
    })
    renderLoginRoute()

    fireEvent.change(screen.getByLabelText('Email address'), {
      target: { value: 'student@example.com' },
    })
    fireEvent.change(screen.getByLabelText('Password'), { target: { value: 'secret' } })
    const password = screen.getByLabelText('Password')
    fireEvent.click(within(screen.getByRole('main')).getByRole('button', { name: 'Sign in' }))

    expect(await screen.findByRole('heading', { name: 'Edit profile' })).toBeVisible()
    expect(screen.queryByRole('heading', { name: 'Welcome back' })).not.toBeInTheDocument()
    expect(login).toHaveBeenCalledWith({ email: 'student@example.com', password: 'secret' })
    expect(password).toHaveValue('')
    login.mockRestore()
  })

  it('renders the login form in German', async () => {
    await i18n.changeLanguage('de')
    renderLoginRoute()

    expect(screen.getByRole('heading', { level: 1, name: 'Willkommen zurück' })).toBeVisible()
    expect(screen.getByLabelText('E-Mail-Adresse')).toBeVisible()
    expect(screen.getByLabelText('Passwort')).toBeVisible()
    expect(within(screen.getByRole('main')).getByRole('button', { name: 'Anmelden' })).toBeVisible()
    expect(screen.getByRole('link', { name: 'Konto erstellen' })).toHaveAttribute(
      'href',
      '/register',
    )
  })
})
