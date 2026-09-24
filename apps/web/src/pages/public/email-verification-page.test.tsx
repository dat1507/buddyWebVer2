import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { sessionClient } from '@/features/auth/session-client'
import i18n from '@/i18n'
import { ApiError } from '@/lib/api'
import { EmailVerificationPage } from '@/pages/public/email-verification-page'
import { useAuthStore } from '@/stores/auth-store'

const user = {
  id: 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa',
  email: 'student@example.com',
  role: 'USER' as const,
  email_verified: false,
  email_verified_at: null,
}

function renderPage(entry = '/verify-email?token=opaque-fixture-token') {
  return render(
    <MemoryRouter initialEntries={[entry]}>
      <EmailVerificationPage />
    </MemoryRouter>,
  )
}

describe('EMAIL-005 email confirmation UX', () => {
  beforeEach(async () => {
    await i18n.changeLanguage('en')
    useAuthStore.getState().setAuthenticated(user)
  })

  afterEach(() => {
    useAuthStore.getState().resetSession()
    vi.restoreAllMocks()
  })

  it('submits the URL token once, refreshes visible state and exposes only the fixed safe path', async () => {
    const confirm = vi
      .spyOn(sessionClient, 'confirmEmailVerification')
      .mockImplementation(async () => {
        useAuthStore.getState().setAuthenticated({
          ...user,
          email_verified: true,
          email_verified_at: '2026-09-24T12:30:00Z',
        })
        return '/user'
      })
    const storage = vi.spyOn(Storage.prototype, 'setItem')
    renderPage()

    const button = screen.getByRole('button', { name: 'Confirm email' })
    button.focus()
    expect(button).toHaveFocus()
    fireEvent.click(button)

    await waitFor(() => expect(confirm).toHaveBeenCalledWith('opaque-fixture-token'))
    expect(screen.getByRole('heading', { name: 'Email verified' })).toBeVisible()
    expect(screen.getByRole('link', { name: 'Continue to your account' })).toHaveAttribute(
      'href',
      '/user',
    )
    expect(storage).not.toHaveBeenCalled()
  })

  it('handles expired links without rendering or persisting raw token content', async () => {
    vi.spyOn(sessionClient, 'confirmEmailVerification').mockRejectedValue(
      new ApiError(400, 'server'),
    )
    const storage = vi.spyOn(Storage.prototype, 'setItem')
    renderPage('/verify-email?token=secret-expired-value')

    fireEvent.click(screen.getByRole('button', { name: 'Confirm email' }))
    const alert = await screen.findByRole('alert')
    expect(alert).toHaveTextContent(/invalid, expired, or already used/i)
    expect(document.body).not.toHaveTextContent('secret-expired-value')
    expect(storage).not.toHaveBeenCalled()
  })

  it('rejects missing or ambiguous query tokens before any API call', () => {
    const confirm = vi.spyOn(sessionClient, 'confirmEmailVerification').mockResolvedValue('/user')
    const first = renderPage('/verify-email')
    expect(screen.getByRole('alert')).toHaveTextContent('missing a valid token')
    first.unmount()
    renderPage('/verify-email?token=one&token=two')
    expect(screen.getByRole('alert')).toHaveTextContent('missing a valid token')
    expect(confirm).not.toHaveBeenCalled()
  })

  it('keeps an unauthenticated link in memory while sign-in opens in a separate tab', () => {
    useAuthStore.getState().clearSession()
    renderPage()
    const signIn = screen.getByRole('link', { name: 'Sign in in a new tab' })
    expect(signIn).toHaveAttribute('href', '/login')
    expect(signIn).toHaveAttribute('target', '_blank')
  })

  it('renders the confirmation action and live result in German', async () => {
    await i18n.changeLanguage('de')
    vi.spyOn(sessionClient, 'confirmEmailVerification').mockImplementation(async () => {
      useAuthStore.getState().setAuthenticated({
        ...user,
        email_verified: true,
        email_verified_at: '2026-09-24T12:30:00Z',
      })
      return '/user'
    })
    renderPage()
    fireEvent.click(screen.getByRole('button', { name: 'E-Mail bestätigen' }))
    expect(await screen.findByRole('heading', { name: 'E-Mail verifiziert' })).toBeVisible()
  })
})
