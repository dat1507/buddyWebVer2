import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { sessionClient } from '@/features/auth/session-client'
import i18n from '@/i18n'
import { ApiError } from '@/lib/api'
import { SettingsPage } from '@/pages/user/settings-page'
import { useAuthStore } from '@/stores/auth-store'

const user = {
  id: 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa',
  email: 'student@example.com',
  role: 'USER' as const,
  email_verified: false,
  email_verified_at: null,
}

function renderPage() {
  return render(
    <MemoryRouter>
      <SettingsPage />
    </MemoryRouter>,
  )
}

describe('EMAIL-005 settings verification UX', () => {
  beforeEach(async () => {
    await i18n.changeLanguage('en')
    useAuthStore.getState().setAuthenticated(user)
  })

  afterEach(() => {
    useAuthStore.getState().resetSession()
    vi.restoreAllMocks()
  })

  it('shows the current backend state and does not infer verification after resend', async () => {
    const request = vi.spyOn(sessionClient, 'requestEmailVerification').mockResolvedValue()
    renderPage()

    expect(screen.getByRole('status', { name: 'Email verification status' })).toHaveTextContent(
      'Unverified',
    )
    expect(screen.getByText('student@example.com')).toBeVisible()
    fireEvent.click(screen.getByRole('button', { name: 'Send verification email' }))

    await waitFor(() => expect(request).toHaveBeenCalledOnce())
    expect(screen.getByText(/account remains unverified/i)).toBeVisible()
    expect(screen.getByRole('status', { name: 'Email verification status' })).toHaveTextContent(
      'Unverified',
    )
  })

  it('validates keyboard-submitted fields and focuses the first invalid input', () => {
    renderPage()
    const email = screen.getByRole('textbox', { name: 'New email address' })
    fireEvent.submit(email.closest('form')!)
    expect(email).toHaveFocus()
    expect(screen.getByText('Enter your new email address.')).toBeVisible()
  })

  it('immediately renders the replacement address as unverified after a successful change', async () => {
    vi.spyOn(sessionClient, 'changeEmail').mockImplementation(async () => {
      const changed = { ...user, email: 'replacement@example.com' }
      useAuthStore.getState().setAuthenticated(changed)
      return useAuthStore.getState().user!
    })
    renderPage()

    fireEvent.change(screen.getByRole('textbox', { name: 'New email address' }), {
      target: { value: 'replacement@example.com' },
    })
    fireEvent.change(screen.getByLabelText('Current password'), {
      target: { value: 'fixture password' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Change email' }))

    expect(await screen.findByText('replacement@example.com')).toBeVisible()
    expect(screen.getByText(/confirm the link sent to the new address/i)).toBeVisible()
    expect(screen.getByRole('status', { name: 'Email verification status' })).toHaveTextContent(
      'Unverified',
    )
  })

  it('renders throttling feedback and German labels accessibly', async () => {
    await i18n.changeLanguage('de')
    vi.spyOn(sessionClient, 'requestEmailVerification').mockRejectedValue(
      new ApiError(429, 'rateLimited', 30),
    )
    renderPage()

    expect(screen.getByRole('heading', { name: 'Einstellungen' })).toBeVisible()
    fireEvent.click(screen.getByRole('button', { name: 'Verifizierungs-E-Mail senden' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('Zu viele Versuche')
    expect(screen.getByRole('status', { name: 'Status der E-Mail-Verifizierung' })).toBeVisible()
  })
})
