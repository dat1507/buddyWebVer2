import { QueryClientProvider } from '@tanstack/react-query'
import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { MemoryRouter } from 'react-router'
import { afterEach, beforeEach, describe, expect, it, vi, type MockInstance } from 'vitest'

import App from '@/App'
import { sessionClient } from '@/features/auth/session-client'
import type { OwnProfile } from '@/features/profile/profile'
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

const completeProfile = {
  id: profileId,
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
  preferences: { preferred_activity_ids: [musicId] },
  matching_opt_in: true,
  avatar: {
    id: photoId,
    mime_type: 'image/webp' as const,
    byte_size: 24_680,
    width: 800,
    height: 800,
    processing_status: 'READY' as const,
    created_at: '2026-09-20T08:00:00Z',
  },
  interest_ids: [musicId],
  languages: [{ language_code: 'en', proficiency: 'fluent' as const }],
  version: 7,
}

const interestCatalog = {
  locale: 'en',
  items: [{ id: musicId, code: 'music', label: 'Music', category: 'culture' }],
}
const languageCatalog = {
  locale: 'en',
  items: [{ code: 'en', label: 'English' }],
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

describe('FE-029 own profile editing', () => {
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

  it('reuses every onboarding section and refreshes matching readiness after required data is removed', async () => {
    let persistedProfile: OwnProfile = completeProfile

    authenticatedJson.mockImplementation(async (path, options) => {
      if (path === `/profile/photos/${photoId}` && options?.method === 'DELETE') {
        persistedProfile = { ...persistedProfile, avatar: null }
        return undefined
      }
      if (path === '/profile/interests' && options?.method === 'PUT') {
        const body = options.body as { interest_ids: string[] }
        persistedProfile = {
          ...persistedProfile,
          interest_ids: body.interest_ids,
          version: persistedProfile.version + 1,
        }
        return { version: persistedProfile.version, interest_ids: persistedProfile.interest_ids }
      }
      if (path === '/profile') return persistedProfile
      if (path === '/profile/completion') {
        const missing = [
          ...(persistedProfile.avatar ? [] : ['AVATAR' as const]),
          ...(persistedProfile.interest_ids.length > 0 ? [] : ['INTERESTS' as const]),
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
      if (path === '/interests?locale=en') return interestCatalog
      if (path === '/languages?locale=en') return languageCatalog
      if (path === `/profile/photos/${photoId}/url`) {
        return { id: photoId, url: 'https://media.example.test/avatar', expires_in: 120 }
      }
      throw new Error(`Unexpected test path: ${path}`)
    })

    renderPage()

    expect(await screen.findByRole('heading', { level: 1, name: 'Edit profile' })).toBeVisible()
    expect(screen.getByRole('heading', { level: 2, name: 'Profile basics' })).toBeVisible()
    expect(screen.getByRole('heading', { level: 2, name: 'Interests and languages' })).toBeVisible()
    expect(
      screen.getByRole('heading', { level: 2, name: 'Availability and preferences' }),
    ).toBeVisible()
    expect(await screen.findByText('Ready for matching')).toBeVisible()
    expect(screen.getByRole('link', { name: 'Edit Profile' })).toHaveAttribute(
      'aria-current',
      'page',
    )

    fireEvent.click(screen.getByRole('button', { name: 'Remove current photo' }))
    fireEvent.click(await screen.findByRole('button', { name: 'Remove photo' }))

    expect(await screen.findByText('New matching is disabled')).toBeVisible()
    expect(
      within(
        screen.getByRole('list', { name: 'Required profile details still missing' }),
      ).getByText('Profile photo'),
    ).toBeVisible()

    const musicSelections = screen.getAllByRole('checkbox', { name: 'Music' })
    fireEvent.click(musicSelections[0])
    fireEvent.click(screen.getByRole('button', { name: 'Save interests and languages' }))

    expect(await screen.findByText('Interests')).toBeVisible()
    expect(authenticatedJson).toHaveBeenCalledWith('/profile/interests', {
      method: 'PUT',
      body: { version: 7, interest_ids: [] },
    })
  })

  it('keeps a rejected student-type edit and reloads the unchanged saved profile after a 409', async () => {
    authenticatedJson.mockImplementation(async (path, options) => {
      if (path === '/profile' && options?.method === 'PUT') {
        throw new ApiError(409, 'conflict')
      }
      if (path === '/profile') return completeProfile
      if (path === '/profile/completion') {
        return {
          status: 'COMPLETE',
          percentage: 100,
          missing_fields: [],
          matching_eligible: false,
          reasons: ['ACTIVE_MATCH_RESERVATION'],
        }
      }
      if (path === '/interests?locale=en') return interestCatalog
      if (path === '/languages?locale=en') return languageCatalog
      if (path === `/profile/photos/${photoId}/url`) {
        return { id: photoId, url: 'https://media.example.test/avatar', expires_in: 120 }
      }
      throw new Error(`Unexpected test path: ${path}`)
    })

    renderPage()

    const vietnamese = await screen.findByRole('radio', { name: 'Vietnamese student' })
    const international = screen.getByRole('radio', { name: 'International student' })
    expect(vietnamese).toBeChecked()
    fireEvent.click(international)
    fireEvent.click(screen.getByRole('button', { name: 'Save profile basics' }))

    expect(await screen.findByText(/student type is locked by an active match/i)).toBeVisible()
    expect(international).toBeChecked()
    expect(completeProfile.student_type).toBe('VIETNAMESE')

    fireEvent.click(screen.getByRole('button', { name: 'Reload saved profile' }))
    await waitFor(() => expect(vietnamese).toBeChecked())
    expect(international).not.toBeChecked()
    expect(authenticatedJson).toHaveBeenCalledWith(
      '/profile',
      expect.objectContaining({
        method: 'PUT',
        body: expect.objectContaining({ version: 7, student_type: 'INTERNATIONAL' }),
      }),
    )
  })
})
