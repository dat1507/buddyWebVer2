import { QueryClientProvider } from '@tanstack/react-query'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router'
import { afterEach, beforeEach, describe, expect, it, vi, type MockInstance } from 'vitest'

import App from '@/App'
import { sessionClient } from '@/features/auth/session-client'
import i18n from '@/i18n'
import { ApiError } from '@/lib/api'
import { queryClient } from '@/lib/query-client'
import { useAuthStore } from '@/stores/auth-store'

const user = {
  id: 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa',
  email: 'student@example.com',
  role: 'USER' as const,
  email_verified: false,
}

const draftProfile = {
  id: 'bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb',
  full_name: null,
  display_name: null,
  student_type: null,
  nationality: null,
  major: null,
  study_year: null,
  bio: null,
  version: 1,
}

const savedProfile = {
  ...draftProfile,
  full_name: 'Nguyen Van An',
  display_name: 'An',
  student_type: 'INTERNATIONAL' as const,
  nationality: 'Vietnamese',
  major: 'Computer Science',
  study_year: 3,
  bio: 'I enjoy meeting students from around the world.',
  version: 2,
}

function renderPage() {
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={['/user/onboarding']}>
        <App />
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

describe('FE-025 onboarding identity step', () => {
  let authenticatedJson: MockInstance<typeof sessionClient.authenticatedJson>

  beforeEach(async () => {
    await i18n.changeLanguage('en')
    queryClient.clear()
    useAuthStore.getState().setAuthenticated(user)
    authenticatedJson = vi.spyOn(sessionClient, 'authenticatedJson').mockResolvedValue(draftProfile)
  })

  afterEach(() => {
    cleanup()
    queryClient.clear()
    useAuthStore.getState().resetSession()
    vi.restoreAllMocks()
  })

  it('starts with no student type and never infers it from nationality', async () => {
    renderPage()

    expect(
      await screen.findByRole('heading', { level: 1, name: 'Tell us about yourself' }),
    ).toBeVisible()
    const vietnamese = screen.getByRole('radio', { name: 'Vietnamese student' })
    const international = screen.getByRole('radio', { name: 'International student' })
    expect(vietnamese).not.toBeChecked()
    expect(international).not.toBeChecked()
    fireEvent.change(screen.getByLabelText(/Nationality/), { target: { value: 'Vietnamese' } })
    expect(vietnamese).not.toBeChecked()
    expect(international).not.toBeChecked()
    expect(
      screen.getByText(/We will look for an international student as your buddy/),
    ).toBeVisible()
    expect(screen.getByText(/We will look for a Vietnamese student as your buddy/)).toBeVisible()
  })

  it('resumes every Step 1 field from the persisted own profile', async () => {
    authenticatedJson.mockResolvedValue(savedProfile)
    renderPage()

    expect(await screen.findByLabelText('Full name')).toHaveValue('Nguyen Van An')
    expect(screen.getByLabelText(/Display name/)).toHaveValue('An')
    expect(screen.getByRole('radio', { name: 'International student' })).toBeChecked()
    expect(screen.getByLabelText(/Major or study program/)).toHaveValue('Computer Science')
    expect(screen.getByLabelText(/Study year/)).toHaveValue(3)
    expect(screen.getByLabelText(/Nationality/)).toHaveValue('Vietnamese')
    expect(screen.getByLabelText(/About you/)).toHaveValue(
      'I enjoy meeting students from around the world.',
    )
  })

  it('validates required identity fields and focuses the first error before saving', async () => {
    renderPage()
    await screen.findByLabelText('Full name')

    fireEvent.click(screen.getByRole('button', { name: 'Save Step 1' }))

    expect(screen.getByText('Enter your full name.')).toBeVisible()
    expect(screen.getByText('Choose how you are joining the Buddy Program.')).toBeVisible()
    expect(screen.getByLabelText('Full name')).toHaveFocus()
    expect(authenticatedJson).toHaveBeenCalledOnce()
  })

  it('saves normalized fields with the persisted version and restores them after reload', async () => {
    authenticatedJson
      .mockReset()
      .mockResolvedValueOnce(draftProfile)
      .mockResolvedValueOnce(savedProfile)
    const firstRender = renderPage()
    await screen.findByLabelText('Full name')

    fireEvent.change(screen.getByLabelText('Full name'), {
      target: { value: '  Nguyen Van An  ' },
    })
    fireEvent.change(screen.getByLabelText(/Display name/), { target: { value: ' An ' } })
    fireEvent.click(screen.getByRole('radio', { name: 'International student' }))
    fireEvent.change(screen.getByLabelText(/Major or study program/), {
      target: { value: ' Computer Science ' },
    })
    fireEvent.change(screen.getByLabelText(/Study year/), { target: { value: '3' } })
    fireEvent.change(screen.getByLabelText(/Nationality/), {
      target: { value: ' Vietnamese ' },
    })
    fireEvent.change(screen.getByLabelText(/About you/), {
      target: { value: ' I enjoy meeting students from around the world. ' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Save Step 1' }))

    expect(await screen.findByText('Step 1 saved to your profile.')).toBeVisible()
    expect(authenticatedJson).toHaveBeenNthCalledWith(2, '/profile', {
      method: 'PUT',
      body: {
        version: 1,
        full_name: 'Nguyen Van An',
        display_name: 'An',
        student_type: 'INTERNATIONAL',
        major: 'Computer Science',
        study_year: 3,
        nationality: 'Vietnamese',
        bio: 'I enjoy meeting students from around the world.',
      },
    })

    firstRender.unmount()
    queryClient.clear()
    authenticatedJson.mockReset().mockResolvedValue(savedProfile)
    renderPage()
    expect(await screen.findByLabelText('Full name')).toHaveValue('Nguyen Van An')
    expect(screen.getByRole('radio', { name: 'International student' })).toBeChecked()
    expect(screen.getByLabelText(/Study year/)).toHaveValue(3)
  })

  it('keeps entries on the step and announces sanitized server validation failure', async () => {
    authenticatedJson
      .mockReset()
      .mockResolvedValueOnce(draftProfile)
      .mockRejectedValueOnce(new ApiError(422, 'validation'))
    renderPage()
    const fullName = await screen.findByLabelText('Full name')
    fireEvent.change(fullName, { target: { value: 'Saved locally' } })
    fireEvent.click(screen.getByRole('radio', { name: 'Vietnamese student' }))
    fireEvent.click(screen.getByRole('button', { name: 'Save Step 1' }))

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Some profile details were not accepted. Review the fields and try again.',
    )
    expect(fullName).toHaveValue('Saved locally')
    expect(screen.getByRole('heading', { name: 'Tell us about yourself' })).toBeVisible()
    expect(authenticatedJson).toHaveBeenCalledTimes(2)
  })

  it('localizes labels and opposite-group guidance in German', async () => {
    await i18n.changeLanguage('de')
    renderPage()

    expect(
      await screen.findByRole('heading', { level: 1, name: 'Erzähl uns etwas über dich' }),
    ).toBeVisible()
    expect(screen.getByLabelText('Vollständiger Name')).toBeVisible()
    expect(screen.getByRole('radio', { name: 'Vietnamesische Studierende' })).not.toBeChecked()
    expect(screen.getByText(/Wir suchen eine internationale Person als Buddy/)).toBeVisible()
    expect(screen.getByText(/Wir suchen eine vietnamesische Person als Buddy/)).toBeVisible()
    expect(screen.getByRole('button', { name: 'Schritt 1 speichern' })).toBeVisible()
  })

  it('shows an accessible retry state when the saved profile cannot be loaded', async () => {
    authenticatedJson.mockRejectedValue(new ApiError(503, 'server'))
    renderPage()

    expect(await screen.findByRole('alert', undefined, { timeout: 3000 })).toHaveTextContent(
      'We could not load your saved profile.',
    )
    expect(screen.getByRole('button', { name: 'Try again' })).toBeEnabled()
    expect(screen.queryByLabelText('Full name')).not.toBeInTheDocument()
    await waitFor(() => expect(authenticatedJson).toHaveBeenCalledTimes(2))
  })
})
