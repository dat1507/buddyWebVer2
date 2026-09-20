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

const musicId = 'bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb'
const languageExchangeId = 'cccccccc-cccc-4ccc-8ccc-cccccccccccc'

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

function catalogResponse(path: string) {
  if (path === '/profile') return profile
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

describe('FE-026 onboarding interests and languages step', () => {
  let authenticatedJson: MockInstance<typeof sessionClient.authenticatedJson>

  beforeEach(async () => {
    await i18n.changeLanguage('en')
    queryClient.clear()
    useAuthStore.getState().setAuthenticated(user)
    authenticatedJson = vi
      .spyOn(sessionClient, 'authenticatedJson')
      .mockImplementation(async (path) => catalogResponse(path))
  })

  afterEach(() => {
    cleanup()
    queryClient.clear()
    useAuthStore.getState().resetSession()
    vi.restoreAllMocks()
  })

  it('resumes saved stable selections and filters the API interest catalog', async () => {
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
  })

  it('saves both replacement sets in version order and restores the canonical result', async () => {
    authenticatedJson.mockImplementation(async (path) => {
      if (path === '/profile/interests') {
        return { version: 4, interest_ids: [musicId, languageExchangeId] }
      }
      if (path === '/profile/languages') {
        return {
          version: 5,
          languages: [
            { language_code: 'de', proficiency: 'native' },
            { language_code: 'en', proficiency: 'fluent' },
          ],
        }
      }
      return catalogResponse(path)
    })
    const firstRender = renderPage()
    await screen.findByRole('checkbox', { name: 'Music' })

    fireEvent.click(screen.getByRole('checkbox', { name: 'Language Exchange' }))
    fireEvent.click(screen.getByRole('checkbox', { name: 'German' }))
    fireEvent.change(screen.getByLabelText('Proficiency in German'), {
      target: { value: 'native' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Save Step 2' }))

    expect(await screen.findByText('Step 2 saved to your profile.')).toBeVisible()
    expect(authenticatedJson).toHaveBeenCalledWith('/profile/interests', {
      method: 'PUT',
      body: {
        version: 3,
        interest_ids: [musicId, languageExchangeId],
      },
    })
    expect(authenticatedJson).toHaveBeenCalledWith('/profile/languages', {
      method: 'PUT',
      body: {
        version: 4,
        languages: [
          { language_code: 'en', proficiency: 'fluent' },
          { language_code: 'de', proficiency: 'native' },
        ],
      },
    })

    firstRender.unmount()
    queryClient.clear()
    authenticatedJson.mockImplementation(async (path) => {
      if (path === '/profile') {
        return {
          ...profile,
          interest_ids: [musicId, languageExchangeId],
          languages: [
            { language_code: 'de', proficiency: 'native' },
            { language_code: 'en', proficiency: 'fluent' },
          ],
          version: 5,
        }
      }
      return catalogResponse(path)
    })
    renderPage()
    expect(await screen.findByRole('checkbox', { name: 'Language Exchange' })).toBeChecked()
    expect(screen.getByRole('checkbox', { name: 'German' })).toBeChecked()
    expect(screen.getByLabelText('Proficiency in German')).toHaveValue('native')
  })

  it('refetches localized labels while preserving selections by stable ID and code', async () => {
    renderPage()
    expect(await screen.findByRole('checkbox', { name: 'Music' })).toBeChecked()

    fireEvent.click(screen.getByRole('button', { name: 'Current language: EN. Switch to German' }))

    expect(await screen.findByRole('checkbox', { name: 'Musik' })).toBeChecked()
    expect(screen.getByRole('checkbox', { name: 'Englisch' })).toBeChecked()
    expect(screen.getByLabelText('Sprachniveau in Englisch')).toHaveValue('fluent')
    expect(authenticatedJson).toHaveBeenCalledWith('/interests?locale=de', expect.any(Object))
    expect(authenticatedJson).toHaveBeenCalledWith('/languages?locale=de', expect.any(Object))
  })

  it('shows retry controls for unavailable catalogs and recovers both independently', async () => {
    let interestAttempts = 0
    let languageAttempts = 0
    authenticatedJson.mockImplementation(async (path) => {
      if (path.startsWith('/interests')) {
        interestAttempts += 1
        if (interestAttempts <= 2) throw new ApiError(503, 'server')
      }
      if (path.startsWith('/languages')) {
        languageAttempts += 1
        if (languageAttempts <= 2) throw new ApiError(503, 'server')
      }
      return catalogResponse(path)
    })
    renderPage()

    expect(
      await screen.findByText('The interest catalog could not be loaded.', undefined, {
        timeout: 3000,
      }),
    ).toBeVisible()
    expect(screen.getByText('The language catalog could not be loaded.')).toBeVisible()
    const retryButtons = screen.getAllByRole('button', { name: 'Try again' })
    expect(retryButtons).toHaveLength(2)
    fireEvent.click(retryButtons[0])
    fireEvent.click(retryButtons[1])

    expect(await screen.findByRole('checkbox', { name: 'Music' })).toBeChecked()
    expect(await screen.findByRole('checkbox', { name: 'English' })).toBeChecked()
  })

  it('prevents duplicate selections and disables catalog options at both limits', async () => {
    const interestItems = Array.from({ length: 21 }, (_, index) => ({
      id: `00000000-0000-4000-8000-${String(index + 1).padStart(12, '0')}`,
      code: `interest-${index + 1}`,
      label: `Interest ${index + 1}`,
      category: 'test',
    }))
    const languageItems = Array.from({ length: 11 }, (_, index) => ({
      code: `x${String.fromCharCode(97 + index)}`,
      label: `Language ${index + 1}`,
    }))
    authenticatedJson.mockImplementation(async (path) => {
      if (path === '/profile') return { ...profile, interest_ids: [], languages: [] }
      if (path.startsWith('/interests')) return { locale: 'en', items: interestItems }
      if (path.startsWith('/languages')) return { locale: 'en', items: languageItems }
      throw new Error(`Unexpected test path: ${path}`)
    })
    renderPage()
    await screen.findByRole('checkbox', { name: 'Interest 1' })

    for (let index = 1; index <= 20; index += 1) {
      fireEvent.click(screen.getByRole('checkbox', { name: `Interest ${index}` }))
    }
    expect(screen.getByText('20 of 20 interests selected')).toBeVisible()
    expect(screen.getByRole('checkbox', { name: 'Interest 21' })).toBeDisabled()

    fireEvent.click(screen.getByRole('checkbox', { name: 'Interest 1' }))
    fireEvent.click(screen.getByRole('checkbox', { name: 'Interest 21' }))
    expect(screen.getByText('20 of 20 interests selected')).toBeVisible()
    expect(screen.getByRole('checkbox', { name: 'Interest 1' })).toBeDisabled()

    for (let index = 1; index <= 10; index += 1) {
      fireEvent.click(screen.getByRole('checkbox', { name: `Language ${index}` }))
    }
    expect(screen.getByText('10 of 10 languages selected')).toBeVisible()
    expect(screen.getByRole('checkbox', { name: 'Language 11' })).toBeDisabled()
    expect(screen.getAllByLabelText(/Proficiency in Language/)).toHaveLength(10)
  }, 10_000)

  it('keeps selections on the step and announces a sanitized failed save', async () => {
    authenticatedJson.mockImplementation(async (path) => {
      if (path === '/profile/interests') throw new ApiError(422, 'validation')
      return catalogResponse(path)
    })
    renderPage()
    await screen.findByRole('checkbox', { name: 'Language Exchange' })
    fireEvent.click(screen.getByRole('checkbox', { name: 'Language Exchange' }))
    fireEvent.click(screen.getByRole('button', { name: 'Save Step 2' }))

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Some selections were not accepted. Review them and try again.',
    )
    expect(screen.getByRole('checkbox', { name: 'Language Exchange' })).toBeChecked()
    expect(screen.getByRole('heading', { name: 'What do you enjoy?' })).toBeVisible()
    expect(screen.getByText('2 of 20 interests selected')).toBeVisible()
  })

  it('reconciles the profile version before retrying a partially completed save', async () => {
    let profileReads = 0
    let languageWrites = 0
    authenticatedJson.mockImplementation(async (path) => {
      if (path === '/profile') {
        profileReads += 1
        return profileReads === 1
          ? profile
          : { ...profile, interest_ids: [musicId, languageExchangeId], version: 4 }
      }
      if (path === '/profile/interests') {
        return { version: 4, interest_ids: [musicId, languageExchangeId] }
      }
      if (path === '/profile/languages') {
        languageWrites += 1
        if (languageWrites === 1) throw new ApiError(422, 'validation')
        return {
          version: 5,
          languages: [
            { language_code: 'de', proficiency: 'beginner' },
            { language_code: 'en', proficiency: 'fluent' },
          ],
        }
      }
      return catalogResponse(path)
    })
    renderPage()
    await screen.findByRole('checkbox', { name: 'Language Exchange' })
    fireEvent.click(screen.getByRole('checkbox', { name: 'Language Exchange' }))
    fireEvent.click(screen.getByRole('checkbox', { name: 'German' }))
    fireEvent.click(screen.getByRole('button', { name: 'Save Step 2' }))

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Some selections were not accepted. Review them and try again.',
    )
    expect(screen.getByRole('checkbox', { name: 'Language Exchange' })).toBeChecked()
    expect(screen.getByRole('checkbox', { name: 'German' })).toBeChecked()
    await waitFor(() => expect(profileReads).toBe(2))

    fireEvent.click(screen.getByRole('button', { name: 'Save Step 2' }))
    expect(await screen.findByText('Step 2 saved to your profile.')).toBeVisible()

    const interestWrites = authenticatedJson.mock.calls.filter(
      ([path]) => path === '/profile/interests',
    )
    expect(interestWrites).toHaveLength(1)
    expect(authenticatedJson).toHaveBeenLastCalledWith('/profile/languages', {
      method: 'PUT',
      body: {
        version: 4,
        languages: [
          { language_code: 'en', proficiency: 'fluent' },
          { language_code: 'de', proficiency: 'beginner' },
        ],
      },
    })
  })
})
