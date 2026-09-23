import { QueryClientProvider } from '@tanstack/react-query'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router'
import { afterEach, beforeEach, describe, expect, it, vi, type MockInstance } from 'vitest'

import App from '@/App'
import { sessionClient } from '@/features/auth/session-client'
import i18n from '@/i18n'
import { queryClient } from '@/lib/query-client'
import { useAuthStore } from '@/stores/auth-store'

const user = {
  id: 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa',
  email: 'student@example.com',
  role: 'USER' as const,
  email_verified: false,
}
const musicId = 'bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb'
const sportsId = 'cccccccc-cccc-4ccc-8ccc-cccccccccccc'

const profile = {
  id: 'dddddddd-dddd-4ddd-8ddd-dddddddddddd',
  full_name: 'Nguyen Van An',
  display_name: 'An',
  student_type: 'VIETNAMESE' as const,
  nationality: 'Vietnamese',
  major: 'Computer Science',
  study_year: 3,
  bio: 'Hello',
  home_university: null,
  arrival_date: null,
  departure_date: null,
  availability: null,
  preferences: null,
  matching_opt_in: false,
  avatar: null,
  interest_ids: [musicId],
  languages: [{ language_code: 'en', proficiency: 'fluent' as const }],
  version: 5,
}

const interestCatalogs = {
  en: {
    locale: 'en',
    items: [
      { id: musicId, code: 'music', label: 'Music', category: 'culture' },
      { id: sportsId, code: 'sports', label: 'Sports', category: 'social' },
    ],
  },
  de: {
    locale: 'de',
    items: [
      { id: musicId, code: 'music', label: 'Musik', category: 'culture' },
      { id: sportsId, code: 'sports', label: 'Sport', category: 'social' },
    ],
  },
} as const

const incomplete = {
  status: 'INCOMPLETE' as const,
  percentage: 60,
  missing_fields: ['FULL_NAME', 'LANGUAGES'] as const,
  matching_eligible: false,
  reasons: ['PROFILE_INCOMPLETE', 'MATCHING_OPT_IN_REQUIRED'] as const,
}

const complete = {
  status: 'COMPLETE' as const,
  percentage: 100,
  missing_fields: [],
  matching_eligible: true,
  reasons: [],
}

function renderPage() {
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={['/user/onboarding/preferences']}>
        <App />
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

describe('FE-027 onboarding availability and preferences step', () => {
  let authenticatedJson: MockInstance<typeof sessionClient.authenticatedJson>

  beforeEach(async () => {
    await i18n.changeLanguage('en')
    queryClient.clear()
    useAuthStore.getState().setAuthenticated(user)
    authenticatedJson = vi.spyOn(sessionClient, 'authenticatedJson')
  })

  afterEach(() => {
    cleanup()
    queryClient.clear()
    useAuthStore.getState().resetSession()
    vi.restoreAllMocks()
  })

  it('skips optional availability without fabricating a schedule and links missing fields to their steps', async () => {
    authenticatedJson.mockImplementation(async (path, options) => {
      if (path === '/profile' && options?.method === 'PUT') {
        return { ...profile, ...(options.body as object), version: 6 }
      }
      if (path === '/profile') return profile
      if (path === '/interests?locale=en') return interestCatalogs.en
      if (path === '/profile/completion') return incomplete
      throw new Error(`Unexpected test path: ${path}`)
    })
    renderPage()

    expect(
      await screen.findByRole('heading', { level: 1, name: 'Finish your Buddy profile' }),
    ).toBeVisible()
    await screen.findByRole('checkbox', { name: 'Music' })
    expect(
      screen.getByRole('checkbox', { name: /Add a weekly availability schedule/ }),
    ).not.toBeChecked()
    expect(screen.queryByLabelText('IANA timezone')).not.toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Save and finish onboarding' }))

    expect(await screen.findByText('Your profile still needs a few details')).toBeVisible()
    expect(screen.getByRole('link', { name: /Full name · Review Step 1/ })).toHaveAttribute(
      'href',
      '/user/onboarding',
    )
    expect(screen.getByRole('link', { name: /Languages · Review Step 2/ })).toHaveAttribute(
      'href',
      '/user/onboarding/interests',
    )
    expect(authenticatedJson).toHaveBeenCalledWith('/profile', {
      method: 'PUT',
      body: {
        version: 5,
        availability: null,
        preferences: { preferred_activity_ids: [] },
        matching_opt_in: false,
      },
    })
  })

  it('saves availability, preferred activities and explicit opt-in before opening the dashboard', async () => {
    let completionReads = 0
    authenticatedJson.mockImplementation(async (path, options) => {
      if (path === '/profile' && options?.method === 'PUT') {
        return { ...profile, ...(options.body as object), version: 6 }
      }
      if (path === '/profile') return profile
      if (path === '/interests?locale=en') return interestCatalogs.en
      if (path === '/profile/completion') {
        completionReads += 1
        return completionReads === 1 ? incomplete : complete
      }
      throw new Error(`Unexpected test path: ${path}`)
    })
    renderPage()

    const availability = await screen.findByRole('checkbox', {
      name: /Add a weekly availability schedule/,
    })
    fireEvent.click(availability)
    fireEvent.change(screen.getByLabelText('IANA timezone'), {
      target: { value: 'Europe/Berlin' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Add time slot' }))
    fireEvent.change(screen.getByLabelText('Day for time slot 1'), { target: { value: '5' } })
    fireEvent.change(screen.getByLabelText('Start time'), { target: { value: '1320' } })
    fireEvent.change(screen.getByLabelText('End time'), { target: { value: '60' } })
    fireEvent.click(screen.getByRole('checkbox', { name: 'Sports' }))
    fireEvent.click(screen.getByRole('radio', { name: /Join buddy matching/ }))
    fireEvent.click(screen.getByRole('button', { name: 'Save and finish onboarding' }))

    expect(await screen.findByRole('heading', { name: 'Edit profile' })).toBeVisible()
    expect(authenticatedJson).toHaveBeenCalledWith('/profile', {
      method: 'PUT',
      body: {
        version: 5,
        availability: {
          timezone: 'Europe/Berlin',
          slots: [{ weekday: 5, start_minute: 1320, end_minute: 60 }],
        },
        preferences: { preferred_activity_ids: [sportsId] },
        matching_opt_in: true,
      },
    })
    expect(completionReads).toBeGreaterThanOrEqual(2)
  })

  it('lets a previously opted-in user revoke matching and clear a saved schedule', async () => {
    const savedProfile = {
      ...profile,
      availability: {
        timezone: 'Asia/Ho_Chi_Minh',
        slots: [{ weekday: 1, start_minute: 540, end_minute: 600 }],
      },
      preferences: { preferred_activity_ids: [musicId] },
      matching_opt_in: true,
    }
    let completionReads = 0
    authenticatedJson.mockImplementation(async (path, options) => {
      if (path === '/profile' && options?.method === 'PUT') {
        return { ...savedProfile, ...(options.body as object), version: 6 }
      }
      if (path === '/profile') return savedProfile
      if (path === '/interests?locale=en') return interestCatalogs.en
      if (path === '/profile/completion') {
        completionReads += 1
        return completionReads === 1
          ? incomplete
          : { ...complete, matching_eligible: false, reasons: ['MATCHING_OPT_IN_REQUIRED'] }
      }
      throw new Error(`Unexpected test path: ${path}`)
    })
    renderPage()

    const availability = await screen.findByRole('checkbox', {
      name: /Add a weekly availability schedule/,
    })
    expect(availability).toBeChecked()
    expect(screen.getByRole('radio', { name: /Join buddy matching/ })).toBeChecked()
    fireEvent.click(availability)
    fireEvent.click(screen.getByRole('radio', { name: /Do not join matching yet/ }))
    fireEvent.click(screen.getByRole('button', { name: 'Save and finish onboarding' }))

    expect(await screen.findByRole('heading', { name: 'Edit profile' })).toBeVisible()
    expect(authenticatedJson).toHaveBeenCalledWith('/profile', {
      method: 'PUT',
      body: {
        version: 5,
        availability: null,
        preferences: { preferred_activity_ids: [musicId] },
        matching_opt_in: false,
      },
    })
  })

  it('blocks a zero-length slot locally and preserves the entered schedule', async () => {
    authenticatedJson.mockImplementation(async (path) => {
      if (path === '/profile') return profile
      if (path === '/interests?locale=en') return interestCatalogs.en
      if (path === '/profile/completion') return incomplete
      throw new Error(`Unexpected test path: ${path}`)
    })
    renderPage()

    fireEvent.click(
      await screen.findByRole('checkbox', { name: /Add a weekly availability schedule/ }),
    )
    fireEvent.click(screen.getByRole('button', { name: 'Add time slot' }))
    fireEvent.change(screen.getByLabelText('End time'), { target: { value: '540' } })
    fireEvent.click(screen.getByRole('button', { name: 'Save and finish onboarding' }))

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'A time slot cannot start and end at the same time.',
    )
    expect(screen.getByLabelText('Start time')).toHaveValue('540')
    expect(screen.getByLabelText('End time')).toHaveValue('540')
    expect(
      authenticatedJson.mock.calls.filter(
        ([path, options]) => path === '/profile' && options?.method === 'PUT',
      ),
    ).toHaveLength(0)
  })

  it('localizes the final step and explicit participation choices in German', async () => {
    await i18n.changeLanguage('de')
    authenticatedJson.mockImplementation(async (path) => {
      if (path === '/profile') return profile
      if (path === '/interests?locale=de') return interestCatalogs.de
      if (path === '/profile/completion') return incomplete
      throw new Error(`Unexpected test path: ${path}`)
    })
    renderPage()

    expect(
      await screen.findByRole('heading', { level: 1, name: 'Schließe dein Buddy-Profil ab' }),
    ).toBeVisible()
    await screen.findByRole('checkbox', { name: 'Musik' })
    expect(screen.getByRole('radio', { name: /Am Buddy-Matching teilnehmen/ })).toBeVisible()
    expect(screen.getByRole('radio', { name: /Noch nicht am Matching teilnehmen/ })).toBeChecked()
    expect(
      screen.getByRole('button', { name: 'Speichern und Onboarding abschließen' }),
    ).toBeEnabled()
    await waitFor(() =>
      expect(authenticatedJson).toHaveBeenCalledWith('/profile/completion', expect.any(Object)),
    )
  })
})
