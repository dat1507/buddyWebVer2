import { QueryClientProvider } from '@tanstack/react-query'
import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { MemoryRouter } from 'react-router'
import { afterEach, beforeEach, describe, expect, it, vi, type MockInstance } from 'vitest'

import App from '@/App'
import { sessionClient } from '@/features/auth/session-client'
import type {
  ProfilePreferenceSnapshot,
  ProfilePreferenceUpdate,
} from '@/features/profile/profile-catalog'
import type { OwnProfile, OwnProfileUpdate } from '@/features/profile/profile'
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
const profileId = 'bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb'
const photoId = 'cccccccc-cccc-4ccc-8ccc-cccccccccccc'
const musicId = 'dddddddd-dddd-4ddd-8ddd-dddddddddddd'
const activityId = 'eeeeeeee-eeee-4eee-8eee-eeeeeeeeeeee'

const completeProfile: OwnProfile = {
  id: profileId,
  full_name: 'Nguyen Van An',
  display_name: 'An',
  student_type: 'VIETNAMESE',
  student_type_locked: false,
  nationality: 'Vietnamese',
  major: 'Computer Science',
  study_year: 3,
  bio: 'Hello',
  home_university: null,
  arrival_date: null,
  departure_date: null,
  availability: null,
  preferences: { preferred_activity_ids: [activityId] },
  matching_opt_in: true,
  avatar: {
    id: photoId,
    mime_type: 'image/webp',
    byte_size: 24_680,
    width: 800,
    height: 800,
    processing_status: 'READY',
    created_at: '2026-09-20T08:00:00Z',
  },
  interest_ids: [musicId],
  languages: [{ language_code: 'en', proficiency: 'fluent' }],
  version: 7,
}

const completePreferences: ProfilePreferenceSnapshot = {
  version: 7,
  interest_ids: [musicId],
  custom_interests: [],
  languages: [{ language_code: 'en', proficiency: 'fluent' }],
  custom_languages: [],
  activity_ids: [activityId],
  custom_activities: [{ label: 'Night kayaking' }],
}

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
const activityCatalogs = {
  en: {
    locale: 'en',
    items: [{ id: activityId, code: 'board-games', label: 'Board Games' }],
  },
  de: {
    locale: 'de',
    items: [{ id: activityId, code: 'board-games', label: 'Brettspiele' }],
  },
} as const

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
      <MemoryRouter initialEntries={['/user/profile/edit']}>
        <App />
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

function mockIdentitySurface(
  authenticatedJson: MockInstance<typeof sessionClient.authenticatedJson>,
  readProfile: () => OwnProfile,
  updateProfile?: (body: unknown) => OwnProfile | Promise<OwnProfile>,
) {
  authenticatedJson.mockImplementation(async (path, options) => {
    if (path === '/profile' && options?.method === 'PUT' && updateProfile)
      return updateProfile(options.body)
    if (path === '/profile') return readProfile()
    if (path === '/profile/preferences') return completePreferences
    if (path === '/profile/completion') {
      return {
        status: 'COMPLETE',
        percentage: 100,
        missing_fields: [],
        matching_eligible: true,
        reasons: [],
      }
    }
    if (path === '/interests?locale=en') return interestCatalogs.en
    if (path === '/interests?locale=de') return interestCatalogs.de
    if (path === '/languages?locale=en') return languageCatalogs.en
    if (path === '/languages?locale=de') return languageCatalogs.de
    if (path === '/activities?locale=en') return activityCatalogs.en
    if (path === '/activities?locale=de') return activityCatalogs.de
    if (path === `/profile/photos/${photoId}/url`) {
      return { id: photoId, url: 'https://media.example.test/avatar', expires_in: 120 }
    }
    throw new Error(`Unexpected test path: ${path}`)
  })
}

describe('FE-029 and PREF-004 own profile editing', () => {
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

  it('reuses all onboarding editors and refreshes readiness after required data is removed', async () => {
    let persistedProfile: OwnProfile = completeProfile
    let persistedPreferences = clonePreferences(completePreferences)

    authenticatedJson.mockImplementation(async (path, options) => {
      if (path === `/profile/photos/${photoId}` && options?.method === 'DELETE') {
        persistedProfile = { ...persistedProfile, avatar: null }
        return undefined
      }
      if (path === '/profile/preferences' && options?.method === 'PUT') {
        const update = options.body as ProfilePreferenceUpdate
        persistedPreferences = { ...clonePreferences(update), version: update.version + 1 }
        persistedProfile = {
          ...persistedProfile,
          version: persistedPreferences.version,
          interest_ids: persistedPreferences.interest_ids,
          languages: persistedPreferences.languages,
        }
        return clonePreferences(persistedPreferences)
      }
      if (path === '/profile') return persistedProfile
      if (path === '/profile/preferences') return clonePreferences(persistedPreferences)
      if (path === '/profile/completion') {
        const hasInterest =
          persistedPreferences.interest_ids.length + persistedPreferences.custom_interests.length >
          0
        const missing = [
          ...(persistedProfile.avatar ? [] : ['AVATAR' as const]),
          ...(hasInterest ? [] : ['INTERESTS' as const]),
        ]
        return missing.length === 0
          ? {
              status: 'COMPLETE',
              percentage: 100,
              missing_fields: [],
              matching_eligible: true,
              reasons: [],
            }
          : {
              status: 'INCOMPLETE',
              percentage: 80,
              missing_fields: missing,
              matching_eligible: false,
              reasons: ['PROFILE_INCOMPLETE'],
            }
      }
      if (path === '/interests?locale=en') return interestCatalogs.en
      if (path === '/interests?locale=de') return interestCatalogs.de
      if (path === '/languages?locale=en') return languageCatalogs.en
      if (path === '/languages?locale=de') return languageCatalogs.de
      if (path === '/activities?locale=en') return activityCatalogs.en
      if (path === '/activities?locale=de') return activityCatalogs.de
      if (path === `/profile/photos/${photoId}/url`) {
        return { id: photoId, url: 'https://media.example.test/avatar', expires_in: 120 }
      }
      throw new Error(`Unexpected test path: ${path}`)
    })

    renderPage()

    expect(await screen.findByRole('heading', { level: 1, name: 'Edit profile' })).toBeVisible()
    expect(screen.getByRole('heading', { level: 2, name: 'Profile basics' })).toBeVisible()
    expect(
      await screen.findByRole('heading', { level: 2, name: 'Interests and languages' }),
    ).toBeVisible()
    expect(
      await screen.findByRole('heading', { level: 2, name: 'Availability and preferences' }),
    ).toBeVisible()
    expect(await screen.findByText('Ready for matching')).toBeVisible()
    expect(await screen.findByRole('checkbox', { name: 'Board Games' })).toBeChecked()
    expect(screen.getByRole('button', { name: 'Remove custom value Night kayaking' })).toBeVisible()

    fireEvent.click(screen.getByRole('button', { name: 'Remove current photo' }))
    fireEvent.click(await screen.findByRole('button', { name: 'Remove photo' }))
    expect(await screen.findByText('New matching is disabled')).toBeVisible()
    expect(
      within(
        screen.getByRole('list', { name: 'Required profile details still missing' }),
      ).getByText('Profile photo'),
    ).toBeVisible()

    fireEvent.click(screen.getByRole('checkbox', { name: 'Music' }))
    fireEvent.click(screen.getByRole('button', { name: 'Save interests and languages' }))

    await waitFor(() =>
      expect(authenticatedJson).toHaveBeenCalledWith('/profile/preferences', {
        method: 'PUT',
        body: {
          version: 7,
          interest_ids: [],
          custom_interests: [],
          languages: [{ language_code: 'en', proficiency: 'fluent' }],
          custom_languages: [],
          activity_ids: [activityId],
          custom_activities: [{ label: 'Night kayaking' }],
        },
      }),
    )
    await waitFor(() =>
      expect(
        within(
          screen.getByRole('list', { name: 'Required profile details still missing' }),
        ).getByText('Interests'),
      ).toBeVisible(),
    )
  })

  it('persists a custom Interest while the unrelated Language catalog is still loading', async () => {
    let persistedProfile: OwnProfile = completeProfile
    let persistedPreferences = clonePreferences(completePreferences)
    let releaseLanguageCatalog!: () => void
    let languageCatalogReady = false
    const languageCatalogDelay = new Promise<void>((resolve) => {
      releaseLanguageCatalog = resolve
    })

    authenticatedJson.mockImplementation(async (path, options) => {
      if (path === '/profile/preferences' && options?.method === 'PUT') {
        const update = options.body as ProfilePreferenceUpdate
        persistedPreferences = { ...clonePreferences(update), version: update.version + 1 }
        persistedProfile = {
          ...persistedProfile,
          version: persistedPreferences.version,
          interest_ids: persistedPreferences.interest_ids,
          languages: persistedPreferences.languages,
        }
        return clonePreferences(persistedPreferences)
      }
      if (path === '/profile') return persistedProfile
      if (path === '/profile/preferences') return clonePreferences(persistedPreferences)
      if (path === '/profile/completion') {
        return {
          status: 'COMPLETE',
          percentage: 100,
          missing_fields: [],
          matching_eligible: true,
          reasons: [],
        }
      }
      if (path === '/interests?locale=en') return interestCatalogs.en
      if (path === '/interests?locale=de') return interestCatalogs.de
      if (path === '/languages?locale=en') {
        if (!languageCatalogReady) await languageCatalogDelay
        return languageCatalogs.en
      }
      if (path === '/languages?locale=de') return languageCatalogs.de
      if (path === '/activities?locale=en') return activityCatalogs.en
      if (path === '/activities?locale=de') return activityCatalogs.de
      if (path === `/profile/photos/${photoId}/url`) {
        return { id: photoId, url: 'https://media.example.test/avatar', expires_in: 120 }
      }
      throw new Error(`Unexpected test path: ${path}`)
    })

    const firstRender = renderPage()
    const customInterest = await screen.findByLabelText('Add a custom interest')
    fireEvent.change(customInterest, { target: { value: 'Formula 1' } })
    fireEvent.click(screen.getByRole('button', { name: 'Add custom interest' }))
    expect(screen.getByRole('button', { name: 'Remove custom value Formula 1' })).toBeVisible()
    const save = screen.getByRole('button', { name: 'Save interests and languages' })
    expect(save).toBeEnabled()
    fireEvent.click(save)

    await waitFor(() =>
      expect(authenticatedJson).toHaveBeenCalledWith('/profile/preferences', {
        method: 'PUT',
        body: {
          version: 7,
          interest_ids: [musicId],
          custom_interests: [{ label: 'Formula 1' }],
          languages: [{ language_code: 'en', proficiency: 'fluent' }],
          custom_languages: [],
          activity_ids: [activityId],
          custom_activities: [{ label: 'Night kayaking' }],
        },
      }),
    )
    expect(
      authenticatedJson.mock.calls.filter(
        ([path, options]) => path === '/profile/preferences' && options?.method === 'PUT',
      ),
    ).toHaveLength(1)
    expect(await screen.findByText('Interests and languages saved.')).toBeVisible()

    languageCatalogReady = true
    releaseLanguageCatalog()
    firstRender.unmount()
    queryClient.clear()
    renderPage()

    expect(
      await screen.findByRole('button', { name: 'Remove custom value Formula 1' }),
    ).toBeVisible()
  })

  it('treats custom Interest and Language as completion signals while Activity stays optional', async () => {
    const customOnlyProfile: OwnProfile = {
      ...completeProfile,
      avatar: null,
      preferences: null,
      interest_ids: [],
      languages: [],
    }
    const customOnlyPreferences: ProfilePreferenceSnapshot = {
      version: 7,
      interest_ids: [],
      custom_interests: [{ label: 'Formula 1' }],
      languages: [],
      custom_languages: [{ label: 'Swiss German', proficiency: 'intermediate' }],
      activity_ids: [],
      custom_activities: [],
    }
    authenticatedJson.mockImplementation(async (path) => {
      if (path === '/profile') return customOnlyProfile
      if (path === '/profile/preferences') return customOnlyPreferences
      if (path === '/profile/completion') {
        return {
          status: 'COMPLETE',
          percentage: 100,
          missing_fields: [],
          matching_eligible: true,
          reasons: [],
        }
      }
      if (path === '/interests?locale=en') return interestCatalogs.en
      if (path === '/interests?locale=de') return interestCatalogs.de
      if (path === '/languages?locale=en') return languageCatalogs.en
      if (path === '/languages?locale=de') return languageCatalogs.de
      if (path === '/activities?locale=en') return activityCatalogs.en
      if (path === '/activities?locale=de') return activityCatalogs.de
      throw new Error(`Unexpected test path: ${path}`)
    })
    renderPage()

    expect(await screen.findByText('Ready for matching')).toBeVisible()
    expect(
      await screen.findByRole('button', { name: 'Remove custom value Formula 1' }),
    ).toBeVisible()
    expect(screen.getByRole('button', { name: 'Remove custom value Swiss German' })).toBeVisible()
    expect(await screen.findByText('0 of 20 preferred activities selected')).toBeVisible()
  })

  it('keeps student type editable and saves an actual transition without an active match', async () => {
    let persistedProfile = completeProfile
    mockIdentitySurface(
      authenticatedJson,
      () => persistedProfile,
      (body) => {
        const update = body as OwnProfileUpdate
        persistedProfile = {
          ...persistedProfile,
          ...update,
          version: update.version + 1,
        }
        return persistedProfile
      },
    )
    renderPage()

    const international = await screen.findByRole('radio', { name: 'International student' })
    expect(international).toBeEnabled()
    fireEvent.click(international)
    fireEvent.change(screen.getByLabelText(/Display name/), { target: { value: 'Updated An' } })
    fireEvent.click(screen.getByRole('button', { name: 'Save profile basics' }))

    expect(await screen.findByText('Profile basics saved.')).toBeVisible()
    expect(authenticatedJson).toHaveBeenCalledWith(
      '/profile',
      expect.objectContaining({
        method: 'PUT',
        body: expect.objectContaining({
          version: 7,
          display_name: 'Updated An',
          student_type: 'INTERNATIONAL',
        }),
      }),
    )
  })

  it('locks only student type while saving unrelated profile fields with the current value', async () => {
    let persistedProfile: OwnProfile = { ...completeProfile, student_type_locked: true }
    mockIdentitySurface(
      authenticatedJson,
      () => persistedProfile,
      (body) => {
        const update = body as OwnProfileUpdate
        persistedProfile = {
          ...persistedProfile,
          ...update,
          student_type_locked: true,
          version: update.version + 1,
        }
        return persistedProfile
      },
    )
    renderPage()

    const vietnamese = await screen.findByRole('radio', { name: 'Vietnamese student' })
    const international = screen.getByRole('radio', { name: 'International student' })
    expect(vietnamese).toBeChecked()
    expect(vietnamese).toBeDisabled()
    expect(international).toBeDisabled()
    expect(vietnamese).toHaveAccessibleDescription(/cannot be changed while you have an active/i)
    expect(screen.getByText(/You can still edit the rest of your profile/i)).toBeVisible()

    const displayName = screen.getByLabelText(/Display name/)
    expect(displayName).toBeEnabled()
    fireEvent.change(displayName, { target: { value: 'Still editable' } })
    fireEvent.click(screen.getByRole('button', { name: 'Save profile basics' }))

    expect(await screen.findByText('Profile basics saved.')).toBeVisible()
    expect(authenticatedJson).toHaveBeenCalledWith(
      '/profile',
      expect.objectContaining({
        method: 'PUT',
        body: expect.objectContaining({
          display_name: 'Still editable',
          student_type: 'VIETNAMESE',
        }),
      }),
    )
  })

  it('reconciles a stale editable form after the typed active-match conflict', async () => {
    let locked = false
    mockIdentitySurface(
      authenticatedJson,
      () => ({ ...completeProfile, student_type_locked: locked }),
      () => {
        locked = true
        throw new ApiError(409, 'conflict', null, 'STUDENT_TYPE_LOCKED_ACTIVE_MATCH')
      },
    )
    renderPage()

    const vietnamese = await screen.findByRole('radio', { name: 'Vietnamese student' })
    const international = screen.getByRole('radio', { name: 'International student' })
    const displayName = screen.getByLabelText(/Display name/)
    fireEvent.change(displayName, { target: { value: 'Safe unsaved edit' } })
    fireEvent.click(international)
    fireEvent.click(screen.getByRole('button', { name: 'Save profile basics' }))

    expect(
      await screen.findByText(/Your student type was not changed because an active Buddy match/i),
    ).toBeVisible()
    await waitFor(() => expect(vietnamese).toBeDisabled())
    expect(vietnamese).toBeChecked()
    expect(international).not.toBeChecked()
    expect(displayName).toHaveValue('Safe unsaved edit')
    expect(screen.queryByText('STUDENT_TYPE_LOCKED_ACTIVE_MATCH')).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Reload saved profile' })).not.toBeInTheDocument()
    expect(
      authenticatedJson.mock.calls.filter(
        ([path, options]) => path === '/profile' && options?.method !== 'PUT',
      ),
    ).toHaveLength(2)
  })

  it('keeps the existing reload flow for a version conflict without locking student type', async () => {
    mockIdentitySurface(
      authenticatedJson,
      () => completeProfile,
      () => {
        throw new ApiError(409, 'conflict')
      },
    )
    renderPage()

    const international = await screen.findByRole('radio', { name: 'International student' })
    fireEvent.click(international)
    fireEvent.click(screen.getByRole('button', { name: 'Save profile basics' }))

    expect(await screen.findByText(/profile changed since this page was loaded/i)).toBeVisible()
    expect(international).toBeEnabled()
    expect(international).toBeChecked()
    expect(screen.getByRole('button', { name: 'Reload saved profile' })).toBeEnabled()
    expect(
      screen.queryByText(/cannot be changed while you have an active/i),
    ).not.toBeInTheDocument()
  })

  it('localizes the locked student-type explanation in German', async () => {
    await i18n.changeLanguage('de')
    const lockedProfile: OwnProfile = { ...completeProfile, student_type_locked: true }
    mockIdentitySurface(authenticatedJson, () => lockedProfile)
    renderPage()

    expect(await screen.findByText(/Studierendentyp kann nicht geändert werden/i)).toBeVisible()
    expect(screen.getByRole('radio', { name: 'Vietnamesische Studierende' })).toBeDisabled()
    expect(screen.getByLabelText(/Anzeigename/)).toBeEnabled()
  })
})
