import { QueryClientProvider } from '@tanstack/react-query'
import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router'
import { afterEach, beforeEach, describe, expect, it, vi, type MockInstance } from 'vitest'

import App from '@/App'
import { sessionClient } from '@/features/auth/session-client'
import type {
  ProfilePreferenceSnapshot,
  ProfilePreferenceUpdate,
} from '@/features/profile/profile-catalog'
import type { ProfileCompletion } from '@/features/profile/profile-completion'
import type { OnboardingPreferencesUpdate, OwnProfile } from '@/features/profile/profile'
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
const musicId = 'bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb'
const boardGamesId = 'cccccccc-cccc-4ccc-8ccc-cccccccccccc'
const sportsId = 'eeeeeeee-eeee-4eee-8eee-eeeeeeeeeeee'

const profile: OwnProfile = {
  id: 'dddddddd-dddd-4ddd-8ddd-dddddddddddd',
  full_name: 'Nguyen Van An',
  display_name: 'An',
  student_type: 'VIETNAMESE',
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
  languages: [{ language_code: 'en', proficiency: 'fluent' }],
  version: 5,
}

const basePreferences: ProfilePreferenceSnapshot = {
  version: 5,
  interest_ids: [musicId],
  custom_interests: [{ label: 'Formula 1' }],
  languages: [{ language_code: 'en', proficiency: 'fluent' }],
  custom_languages: [{ label: 'Swiss German', proficiency: 'intermediate' }],
  activity_ids: [],
  custom_activities: [],
}

const activityCatalogs = {
  en: {
    locale: 'en',
    items: [
      { id: boardGamesId, code: 'board-games', label: 'Board Games' },
      { id: sportsId, code: 'sports', label: 'Sports' },
    ],
  },
  de: {
    locale: 'de',
    items: [
      { id: boardGamesId, code: 'board-games', label: 'Brettspiele' },
      { id: sportsId, code: 'sports', label: 'Sport' },
    ],
  },
} as const

const interestCatalogs = {
  en: {
    locale: 'en',
    items: [{ id: musicId, code: 'music', label: 'Music', category: 'culture' }],
  },
  de: {
    locale: 'de',
    items: [{ id: musicId, code: 'music', label: 'Musik', category: 'culture' }],
  },
} as const

const languageCatalogs = {
  en: { locale: 'en', items: [{ code: 'en', label: 'English' }] },
  de: { locale: 'de', items: [{ code: 'en', label: 'Englisch' }] },
} as const

const incomplete: ProfileCompletion = {
  status: 'INCOMPLETE' as const,
  percentage: 60,
  missing_fields: ['FULL_NAME', 'LANGUAGES'] as const,
  matching_eligible: false,
  reasons: ['PROFILE_INCOMPLETE', 'MATCHING_OPT_IN_REQUIRED'] as const,
}

const complete: ProfileCompletion = {
  status: 'COMPLETE' as const,
  percentage: 100,
  missing_fields: [],
  matching_eligible: true,
  reasons: [],
}

function clonePreferences(preferences: ProfilePreferenceSnapshot): ProfilePreferenceSnapshot {
  return {
    ...preferences,
    interest_ids: [...preferences.interest_ids],
    custom_interests: preferences.custom_interests.map((selection) => ({ ...selection })),
    languages: preferences.languages.map((selection) => ({ ...selection })),
    custom_languages: preferences.custom_languages.map((selection) => ({ ...selection })),
    activity_ids: [...preferences.activity_ids],
    custom_activities: preferences.custom_activities.map((selection) => ({ ...selection })),
  }
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

describe('FE-027 and PREF-004 availability and activity editor', () => {
  let authenticatedJson: MockInstance<typeof sessionClient.authenticatedJson>
  let persistedProfile: OwnProfile
  let persistedPreferences: ProfilePreferenceSnapshot
  let completionReads: number

  function installApi(completionAfterSave = incomplete) {
    authenticatedJson.mockImplementation(async (path, options) => {
      if (path === '/profile/preferences' && options?.method === 'PUT') {
        const update = options.body as ProfilePreferenceUpdate
        persistedPreferences = { ...clonePreferences(update), version: update.version + 1 }
        return clonePreferences(persistedPreferences)
      }
      if (path === '/profile' && options?.method === 'PUT') {
        const update = options.body as OnboardingPreferencesUpdate
        persistedProfile = { ...persistedProfile, ...update, version: update.version + 1 }
        persistedPreferences = { ...persistedPreferences, version: persistedProfile.version }
        return persistedProfile
      }
      if (path === '/profile') return persistedProfile
      if (path === '/profile/preferences') return clonePreferences(persistedPreferences)
      if (path === '/activities?locale=en') return activityCatalogs.en
      if (path === '/activities?locale=de') return activityCatalogs.de
      if (path === '/interests?locale=en') return interestCatalogs.en
      if (path === '/interests?locale=de') return interestCatalogs.de
      if (path === '/languages?locale=en') return languageCatalogs.en
      if (path === '/languages?locale=de') return languageCatalogs.de
      if (path === '/profile/completion') {
        completionReads += 1
        return completionReads === 1 ? incomplete : completionAfterSave
      }
      throw new Error(`Unexpected test path: ${path}`)
    })
  }

  beforeEach(async () => {
    await i18n.changeLanguage('en')
    queryClient.clear()
    useAuthStore.getState().setAuthenticated(user)
    authenticatedJson = vi.spyOn(sessionClient, 'authenticatedJson')
    persistedProfile = profile
    persistedPreferences = clonePreferences(basePreferences)
    completionReads = 0
  })

  afterEach(() => {
    cleanup()
    queryClient.clear()
    useAuthStore.getState().resetSession()
    vi.restoreAllMocks()
  })

  it('keeps Activity optional and omits the preference write when only profile settings change', async () => {
    installApi()
    renderPage()

    expect(
      await screen.findByRole('heading', { level: 1, name: 'Finish your Buddy profile' }),
    ).toBeVisible()
    expect(await screen.findByRole('checkbox', { name: 'Board Games' })).not.toBeChecked()
    expect(
      screen.getByRole('checkbox', { name: /Add a weekly availability schedule/ }),
    ).not.toBeChecked()
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
      body: { version: 5, availability: null, matching_opt_in: false },
    })
    expect(
      authenticatedJson.mock.calls.filter(
        ([path, options]) => path === '/profile/preferences' && options?.method === 'PUT',
      ),
    ).toHaveLength(0)
  })

  it('saves real Activity IDs and custom Activities before the profile mutation', async () => {
    installApi(complete)
    renderPage()

    fireEvent.click(
      await screen.findByRole('checkbox', { name: /Add a weekly availability schedule/ }),
    )
    fireEvent.change(screen.getByLabelText('IANA timezone'), {
      target: { value: 'Europe/Berlin' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Add time slot' }))
    fireEvent.change(screen.getByLabelText('Day for time slot 1'), { target: { value: '5' } })
    fireEvent.change(screen.getByLabelText('Start time'), { target: { value: '1320' } })
    fireEvent.change(screen.getByLabelText('End time'), { target: { value: '60' } })
    fireEvent.click(screen.getByRole('checkbox', { name: 'Sports' }))
    fireEvent.change(screen.getByLabelText('Add a custom activity'), {
      target: { value: 'Night kayaking' },
    })
    fireEvent.keyDown(screen.getByLabelText('Add a custom activity'), { key: 'Enter' })
    fireEvent.click(screen.getByRole('radio', { name: /Join buddy matching/ }))
    fireEvent.click(screen.getByRole('button', { name: 'Save and finish onboarding' }))

    expect(await screen.findByRole('heading', { name: 'Edit profile' })).toBeVisible()
    expect(authenticatedJson).toHaveBeenCalledWith('/profile/preferences', {
      method: 'PUT',
      body: {
        version: 5,
        interest_ids: [musicId],
        custom_interests: [{ label: 'Formula 1' }],
        languages: [{ language_code: 'en', proficiency: 'fluent' }],
        custom_languages: [{ label: 'Swiss German', proficiency: 'intermediate' }],
        activity_ids: [sportsId],
        custom_activities: [{ label: 'Night kayaking' }],
      },
    })
    expect(authenticatedJson).toHaveBeenCalledWith('/profile', {
      method: 'PUT',
      body: {
        version: 6,
        availability: {
          timezone: 'Europe/Berlin',
          slots: [{ weekday: 5, start_minute: 1320, end_minute: 60 }],
        },
        matching_opt_in: true,
      },
    })
  })

  it('round-trips additions and removals across fresh mounts', async () => {
    installApi()
    const firstRender = renderPage()
    fireEvent.click(await screen.findByRole('checkbox', { name: 'Board Games' }))
    fireEvent.change(screen.getByLabelText('Add a custom activity'), {
      target: { value: 'Night kayaking' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Add custom activity' }))
    fireEvent.click(screen.getByRole('button', { name: 'Save and finish onboarding' }))
    expect(await screen.findByText('Availability and preferences saved.')).toBeVisible()

    firstRender.unmount()
    queryClient.clear()
    const secondRender = renderPage()
    expect(await screen.findByRole('checkbox', { name: 'Board Games' })).toBeChecked()
    expect(screen.getByRole('button', { name: 'Remove custom value Night kayaking' })).toBeVisible()

    fireEvent.click(screen.getByRole('checkbox', { name: 'Board Games' }))
    fireEvent.click(screen.getByRole('button', { name: 'Remove custom value Night kayaking' }))
    fireEvent.click(screen.getByRole('button', { name: 'Save and finish onboarding' }))
    expect(await screen.findByText('Availability and preferences saved.')).toBeVisible()

    secondRender.unmount()
    queryClient.clear()
    renderPage()
    expect(await screen.findByRole('checkbox', { name: 'Board Games' })).not.toBeChecked()
    expect(screen.queryByText('Night kayaking')).not.toBeInTheDocument()
  })

  it('prevents predefined and normalized custom Activity duplicates with an explanation', async () => {
    installApi()
    renderPage()
    const input = await screen.findByLabelText('Add a custom activity')

    fireEvent.change(input, { target: { value: '  sports  ' } })
    fireEvent.keyDown(input, { key: 'Enter' })
    expect(await screen.findByRole('alert')).toHaveTextContent(
      'This matches an existing predefined option.',
    )

    fireEvent.change(input, { target: { value: 'Night kayaking' } })
    fireEvent.keyDown(input, { key: 'Enter' })
    fireEvent.change(input, { target: { value: ' night   kayaking ' } })
    fireEvent.keyDown(input, { key: 'Enter' })
    expect(await screen.findByRole('alert')).toHaveTextContent(
      'This custom value is already selected.',
    )
    expect(screen.getAllByText('Night kayaking')).toHaveLength(1)
  })

  it('blocks an invalid slot locally and preserves the entered schedule', async () => {
    installApi()
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

  it('preserves the Activity draft and sanitizes a backend validation failure', async () => {
    installApi()
    authenticatedJson.mockImplementation(async (path, options) => {
      if (path === '/profile/preferences' && options?.method === 'PUT') {
        throw new ApiError(422, 'validation')
      }
      if (path === '/profile') return persistedProfile
      if (path === '/profile/preferences') return clonePreferences(persistedPreferences)
      if (path === '/activities?locale=en') return activityCatalogs.en
      if (path === '/activities?locale=de') return activityCatalogs.de
      if (path === '/profile/completion') return incomplete
      throw new Error(`Unexpected test path: ${path}`)
    })
    renderPage()
    fireEvent.click(await screen.findByRole('checkbox', { name: 'Sports' }))
    fireEvent.click(screen.getByRole('button', { name: 'Save and finish onboarding' }))

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'The server did not accept some availability or preference details.',
    )
    expect(screen.getByRole('checkbox', { name: 'Sports' })).toBeChecked()
    expect(document.body).not.toHaveTextContent('normalized_key')
  })

  it('localizes the final step, Activity catalog and custom controls in German', async () => {
    await i18n.changeLanguage('de')
    installApi()
    renderPage()

    expect(
      await screen.findByRole('heading', { level: 1, name: 'Schließe dein Buddy-Profil ab' }),
    ).toBeVisible()
    expect(await screen.findByRole('checkbox', { name: 'Brettspiele' })).toBeVisible()
    expect(screen.getByLabelText('Benutzerdefinierte Aktivität hinzufügen')).toBeVisible()
    expect(screen.getByRole('radio', { name: /Am Buddy-Matching teilnehmen/ })).toBeVisible()
    expect(
      screen.getByRole('button', { name: 'Speichern und Onboarding abschließen' }),
    ).toBeEnabled()
  })
})
