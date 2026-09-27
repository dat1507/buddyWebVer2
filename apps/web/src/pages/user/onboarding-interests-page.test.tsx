import { QueryClientProvider } from '@tanstack/react-query'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router'
import { afterEach, beforeEach, describe, expect, it, vi, type MockInstance } from 'vitest'

import App from '@/App'
import { sessionClient } from '@/features/auth/session-client'
import type {
  ProfilePreferenceSnapshot,
  ProfilePreferenceUpdate,
} from '@/features/profile/profile-catalog'
import { profileClient } from '@/features/profile/profile-client'
import i18n from '@/i18n'
import { ApiError } from '@/lib/api'
import { queryClient } from '@/lib/query-client'
import { useAuthStore } from '@/stores/auth-store'
import { incompleteProfileCompletion } from '@/test/profile-completion'

const user = {
  id: 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa',
  email: 'student@example.com',
  role: 'USER' as const,
  email_verified: false,
}

const musicId = 'bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb'
const languageExchangeId = 'cccccccc-cccc-4ccc-8ccc-cccccccccccc'
const activityId = 'eeeeeeee-eeee-4eee-8eee-eeeeeeeeeeee'

const profile = {
  id: 'dddddddd-dddd-4ddd-8ddd-dddddddddddd',
  full_name: 'Nguyen Van An',
  display_name: 'An',
  student_type: 'VIETNAMESE' as const,
  nationality: 'Vietnamese',
  major: 'Computer Science',
  study_year: 3,
  bio: 'Hello',
  interest_ids: [musicId],
  languages: [{ language_code: 'en', proficiency: 'fluent' as const }],
  version: 3,
}

const basePreferences: ProfilePreferenceSnapshot = {
  version: 3,
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
    items: [
      { id: musicId, code: 'music', label: 'Music', category: 'culture' },
      {
        id: languageExchangeId,
        code: 'language-exchange',
        label: 'Language Exchange',
        category: 'social',
      },
    ],
  },
  de: {
    locale: 'de',
    items: [
      { id: musicId, code: 'music', label: 'Musik', category: 'culture' },
      {
        id: languageExchangeId,
        code: 'language-exchange',
        label: 'Sprachaustausch',
        category: 'social',
      },
    ],
  },
} as const

const languageCatalogs = {
  en: {
    locale: 'en',
    items: [
      { code: 'en', label: 'English' },
      { code: 'de', label: 'German' },
    ],
  },
  de: {
    locale: 'de',
    items: [
      { code: 'en', label: 'Englisch' },
      { code: 'de', label: 'Deutsch' },
    ],
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

function catalogResponse(path: string, preferences: ProfilePreferenceSnapshot) {
  if (path === '/profile') return profile
  if (path === '/profile/preferences') return clonePreferences(preferences)
  if (path === '/interests?locale=en') return interestCatalogs.en
  if (path === '/interests?locale=de') return interestCatalogs.de
  if (path === '/languages?locale=en') return languageCatalogs.en
  if (path === '/languages?locale=de') return languageCatalogs.de
  throw new Error(`Unexpected test path: ${path}`)
}

function renderPage() {
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={['/user/onboarding/interests']}>
        <App />
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

describe('FE-026 and PREF-004 interests and languages editor', () => {
  let authenticatedJson: MockInstance<typeof sessionClient.authenticatedJson>
  let persistedPreferences: ProfilePreferenceSnapshot

  beforeEach(async () => {
    await i18n.changeLanguage('en')
    queryClient.clear()
    queryClient.setQueryData(['profile', 'completion'], incompleteProfileCompletion)
    useAuthStore.getState().setAuthenticated(user)
    vi.spyOn(profileClient, 'readCompletion').mockResolvedValue(incompleteProfileCompletion)
    persistedPreferences = clonePreferences(basePreferences)
    authenticatedJson = vi
      .spyOn(sessionClient, 'authenticatedJson')
      .mockImplementation(async (path, options) => {
        if (path === '/profile/preferences' && options?.method === 'PUT') {
          const update = options.body as ProfilePreferenceUpdate
          persistedPreferences = { ...clonePreferences(update), version: update.version + 1 }
          return clonePreferences(persistedPreferences)
        }
        return catalogResponse(path, persistedPreferences)
      })
  })

  afterEach(() => {
    cleanup()
    queryClient.clear()
    useAuthStore.getState().resetSession()
    vi.restoreAllMocks()
  })

  it('resumes saved selections, filters the catalog and localizes stable IDs', async () => {
    renderPage()

    expect(
      await screen.findByRole('heading', { level: 1, name: 'What do you enjoy?' }),
    ).toBeVisible()
    expect(await screen.findByRole('checkbox', { name: 'Music' })).toBeChecked()
    expect(screen.getByRole('checkbox', { name: 'Language Exchange' })).not.toBeChecked()
    expect(screen.getByRole('checkbox', { name: 'English' })).toBeChecked()
    expect(screen.getByLabelText('Proficiency in English')).toHaveValue('fluent')

    fireEvent.change(screen.getByLabelText('Search interests'), {
      target: { value: 'language' },
    })
    expect(screen.queryByRole('checkbox', { name: 'Music' })).not.toBeInTheDocument()
    expect(screen.getByRole('checkbox', { name: 'Language Exchange' })).toBeVisible()

    fireEvent.click(screen.getByRole('button', { name: 'Current language: EN. Switch to German' }))
    expect(await screen.findByRole('checkbox', { name: 'Sprachaustausch' })).not.toBeChecked()
    expect(screen.getByRole('checkbox', { name: 'Englisch' })).toBeChecked()
    expect(screen.getByLabelText('Sprachniveau in Englisch')).toHaveValue('fluent')
  })

  it('adds predefined and custom values, saves one atomic payload and reloads labels plus proficiency', async () => {
    const firstRender = renderPage()
    await screen.findByRole('checkbox', { name: 'Music' })

    fireEvent.click(screen.getByRole('checkbox', { name: 'Language Exchange' }))
    fireEvent.change(screen.getByLabelText('Add a custom interest'), {
      target: { value: '  Formula   1  ' },
    })
    fireEvent.keyDown(screen.getByLabelText('Add a custom interest'), { key: 'Enter' })

    fireEvent.click(screen.getByRole('checkbox', { name: 'German' }))
    fireEvent.change(screen.getByLabelText('Proficiency in German'), {
      target: { value: 'native' },
    })
    fireEvent.change(screen.getByLabelText('Proficiency'), {
      target: { value: 'intermediate' },
    })
    fireEvent.change(screen.getByLabelText('Add a custom language'), {
      target: { value: 'Swiss German' },
    })
    fireEvent.keyDown(screen.getByLabelText('Add a custom language'), { key: 'Enter' })
    fireEvent.click(screen.getByRole('button', { name: 'Save Step 2' }))

    expect(await screen.findByText('Step 2 saved to your profile.')).toBeVisible()
    expect(authenticatedJson).toHaveBeenCalledWith('/profile/preferences', {
      method: 'PUT',
      body: {
        version: 3,
        interest_ids: [musicId, languageExchangeId],
        custom_interests: [{ label: 'Formula 1' }],
        languages: [
          { language_code: 'en', proficiency: 'fluent' },
          { language_code: 'de', proficiency: 'native' },
        ],
        custom_languages: [{ label: 'Swiss German', proficiency: 'intermediate' }],
        activity_ids: [activityId],
        custom_activities: [{ label: 'Night kayaking' }],
      },
    })

    firstRender.unmount()
    queryClient.clear()
    renderPage()

    expect(await screen.findByRole('checkbox', { name: 'Language Exchange' })).toBeChecked()
    expect(screen.getByRole('button', { name: 'Remove custom value Formula 1' })).toBeVisible()
    expect(screen.getByRole('checkbox', { name: 'German' })).toBeChecked()
    expect(screen.getByLabelText('Proficiency in German')).toHaveValue('native')
    expect(screen.getByLabelText('Proficiency in Swiss German')).toHaveValue('intermediate')
  })

  it('changes custom-language proficiency and retains the update after reload', async () => {
    persistedPreferences = {
      ...clonePreferences(basePreferences),
      custom_languages: [{ label: 'Swiss German', proficiency: 'beginner' }],
    }
    const firstRender = renderPage()

    const proficiency = await screen.findByLabelText('Proficiency in Swiss German')
    expect(proficiency).toHaveValue('beginner')
    fireEvent.change(proficiency, { target: { value: 'fluent' } })
    fireEvent.click(screen.getByRole('button', { name: 'Save Step 2' }))
    expect(await screen.findByText('Step 2 saved to your profile.')).toBeVisible()

    firstRender.unmount()
    queryClient.clear()
    renderPage()
    expect(await screen.findByLabelText('Proficiency in Swiss German')).toHaveValue('fluent')
  })

  it('removes predefined and custom values and does not restore them on reload', async () => {
    persistedPreferences = {
      ...clonePreferences(basePreferences),
      custom_interests: [{ label: 'Formula 1' }],
      custom_languages: [{ label: 'Swiss German', proficiency: 'intermediate' }],
    }
    const firstRender = renderPage()

    fireEvent.click(await screen.findByRole('checkbox', { name: 'Music' }))
    fireEvent.click(screen.getByRole('button', { name: 'Remove custom value Formula 1' }))
    fireEvent.click(screen.getByRole('checkbox', { name: 'English' }))
    fireEvent.click(screen.getByRole('button', { name: 'Remove custom value Swiss German' }))
    fireEvent.click(screen.getByRole('button', { name: 'Save Step 2' }))
    expect(await screen.findByText('Step 2 saved to your profile.')).toBeVisible()

    firstRender.unmount()
    queryClient.clear()
    renderPage()
    expect(await screen.findByRole('checkbox', { name: 'Music' })).not.toBeChecked()
    expect(screen.getByRole('checkbox', { name: 'English' })).not.toBeChecked()
    expect(screen.queryByText('Formula 1')).not.toBeInTheDocument()
    expect(screen.queryByText('Swiss German')).not.toBeInTheDocument()
  })

  it('explains predefined collisions and normalized duplicates within one kind only', async () => {
    renderPage()
    const customInterest = await screen.findByLabelText('Add a custom interest')

    fireEvent.change(customInterest, { target: { value: '  music  ' } })
    fireEvent.keyDown(customInterest, { key: 'Enter' })
    expect(await screen.findByRole('alert')).toHaveTextContent(
      'This matches an existing predefined option.',
    )

    fireEvent.change(customInterest, { target: { value: 'Formula 1' } })
    fireEvent.keyDown(customInterest, { key: 'Enter' })
    fireEvent.change(customInterest, { target: { value: '  formula   1  ' } })
    fireEvent.keyDown(customInterest, { key: 'Enter' })
    expect(await screen.findByRole('alert')).toHaveTextContent(
      'This custom value is already selected.',
    )
    expect(screen.getAllByText('Formula 1')).toHaveLength(1)

    fireEvent.change(customInterest, { target: { value: 'German' } })
    fireEvent.keyDown(customInterest, { key: 'Enter' })
    expect(screen.getByRole('button', { name: 'Remove custom value German' })).toBeVisible()
  })

  it('combines predefined and custom values when enforcing both limits', async () => {
    persistedPreferences = {
      ...clonePreferences(basePreferences),
      custom_interests: Array.from({ length: 19 }, (_, index) => ({
        label: `Custom interest ${index + 1}`,
      })),
      custom_languages: Array.from({ length: 9 }, (_, index) => ({
        label: `Custom language ${index + 1}`,
        proficiency: 'beginner' as const,
      })),
    }
    renderPage()

    expect(await screen.findByText('20 of 20 interests selected')).toBeVisible()
    expect(screen.getByRole('checkbox', { name: 'Language Exchange' })).toBeDisabled()
    expect(screen.getByLabelText('Add a custom interest')).toBeDisabled()
    expect(screen.getByText('10 of 10 languages selected')).toBeVisible()
    expect(screen.getByRole('checkbox', { name: 'German' })).toBeDisabled()
    expect(screen.getByLabelText('Add a custom language')).toBeDisabled()
  })

  it('keeps the draft and shows a sanitized message when the backend rejects it', async () => {
    authenticatedJson.mockImplementation(async (path, options) => {
      if (path === '/profile/preferences' && options?.method === 'PUT') {
        throw new ApiError(422, 'validation')
      }
      return catalogResponse(path, persistedPreferences)
    })
    renderPage()

    fireEvent.click(await screen.findByRole('checkbox', { name: 'Language Exchange' }))
    fireEvent.click(screen.getByRole('button', { name: 'Save Step 2' }))

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Some selections were not accepted. Review them and try again.',
    )
    expect(screen.getByRole('checkbox', { name: 'Language Exchange' })).toBeChecked()
    expect(document.body).not.toHaveTextContent('normalized_key')
    expect(document.body).not.toHaveTextContent('constraint')
  })

  it('refetches after a stale write and retries the preserved draft with the new version', async () => {
    let preferenceReads = 0
    const putBodies: ProfilePreferenceUpdate[] = []
    authenticatedJson.mockImplementation(async (path, options) => {
      if (path === '/profile/preferences' && options?.method === 'PUT') {
        const update = options.body as ProfilePreferenceUpdate
        putBodies.push(update)
        if (putBodies.length === 1) throw new ApiError(409, 'conflict')
        persistedPreferences = { ...clonePreferences(update), version: update.version + 1 }
        return clonePreferences(persistedPreferences)
      }
      if (path === '/profile/preferences') {
        preferenceReads += 1
        return {
          ...clonePreferences(persistedPreferences),
          version: preferenceReads === 1 ? 3 : 4,
        }
      }
      return catalogResponse(path, persistedPreferences)
    })
    renderPage()

    fireEvent.click(await screen.findByRole('checkbox', { name: 'Language Exchange' }))
    fireEvent.click(screen.getByRole('button', { name: 'Save Step 2' }))
    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Your profile changed in another session.',
    )
    expect(screen.getByRole('checkbox', { name: 'Language Exchange' })).toBeChecked()
    await waitFor(() => expect(preferenceReads).toBeGreaterThanOrEqual(2))

    fireEvent.click(screen.getByRole('button', { name: 'Save Step 2' }))
    expect(await screen.findByText('Step 2 saved to your profile.')).toBeVisible()
    expect(putBodies.map(({ version }) => version)).toEqual([3, 4])
  })

  it('shows independent retry controls when the current-locale catalogs are unavailable', async () => {
    let failInterests = true
    let failLanguages = true
    authenticatedJson.mockImplementation(async (path) => {
      if (path === '/interests?locale=en' && failInterests) throw new ApiError(503, 'server')
      if (path === '/languages?locale=en' && failLanguages) throw new ApiError(503, 'server')
      return catalogResponse(path, persistedPreferences)
    })
    renderPage()

    expect(
      await screen.findByText('The interest catalog could not be loaded.', undefined, {
        timeout: 5000,
      }),
    ).toBeVisible()
    expect(screen.getByText('The language catalog could not be loaded.')).toBeVisible()
    const retryButtons = screen.getAllByRole('button', { name: 'Try again' })
    expect(retryButtons).toHaveLength(2)
    failInterests = false
    failLanguages = false
    fireEvent.click(retryButtons[0])
    fireEvent.click(retryButtons[1])

    expect(await screen.findByRole('checkbox', { name: 'Music' })).toBeChecked()
    expect(await screen.findByRole('checkbox', { name: 'English' })).toBeChecked()
  })
})
