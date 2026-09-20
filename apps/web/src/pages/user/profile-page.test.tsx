import { QueryClientProvider } from '@tanstack/react-query'
import { act, cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
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
const profileId = 'bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb'
const photoId = 'cccccccc-cccc-4ccc-8ccc-cccccccccccc'
const musicId = 'dddddddd-dddd-4ddd-8ddd-dddddddddddd'

const profile = {
  id: profileId,
  full_name: 'Nguyen Van An',
  display_name: 'An',
  student_type: 'VIETNAMESE' as const,
  nationality: 'Vietnamese',
  major: 'Computer Science',
  study_year: 3,
  bio: 'I enjoy helping new students settle in.',
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
  languages: [{ language_code: 'en', proficiency: 'fluent' as const }],
  version: 4,
  password_hash: 'must-never-render',
  raw_credentials: 'must-never-render',
  matching_opt_in: true,
  availability: {
    timezone: 'Asia/Ho_Chi_Minh',
    slots: [{ weekday: 1, start_minute: 540, end_minute: 600 }],
    private_note: 'must-never-render',
  },
  preferences: { preferred_activity_ids: [musicId], private_note: 'must-never-render' },
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

function responseFor(path: string): unknown {
  if (path === '/profile') return profile
  if (path === '/interests?locale=en') return interestCatalogs.en
  if (path === '/interests?locale=de') return interestCatalogs.de
  if (path === '/languages?locale=en') return languageCatalogs.en
  if (path === '/languages?locale=de') return languageCatalogs.de
  if (path === `/profile/photos/${photoId}/url`) {
    return { id: photoId, url: 'https://media.example.test/avatar-one', expires_in: 120 }
  }
  throw new Error(`Unexpected test path: ${path}`)
}

function renderPage() {
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={['/user/profile']}>
        <App />
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

describe('FE-028 own profile view', () => {
  let authenticatedJson: MockInstance<typeof sessionClient.authenticatedJson>

  beforeEach(async () => {
    await i18n.changeLanguage('en')
    queryClient.clear()
    useAuthStore.getState().setAuthenticated(user)
    authenticatedJson = vi
      .spyOn(sessionClient, 'authenticatedJson')
      .mockImplementation(async (path) => responseFor(path))
  })

  afterEach(() => {
    cleanup()
    queryClient.clear()
    useAuthStore.getState().resetSession()
    vi.restoreAllMocks()
  })

  it('renders persisted identity and catalog labels without exposing private response fields', async () => {
    renderPage()

    const card = await screen.findByLabelText('Profile card for An')
    expect(within(card).getByRole('heading', { name: 'An' })).toBeVisible()
    expect(within(card).getByText('Full name: Nguyen Van An')).toBeVisible()
    expect(within(card).getByText('Vietnamese student')).toBeVisible()
    expect(within(card).getByText('I enjoy helping new students settle in.')).toBeVisible()
    expect(within(card).getByText('Computer Science')).toBeVisible()
    expect(within(card).getByText('Year 3')).toBeVisible()
    expect(within(card).getByText('Vietnamese')).toBeVisible()
    expect(await within(card).findByText('Music')).toBeVisible()
    expect(await within(card).findByText('English')).toBeVisible()
    expect(within(card).getByText('Fluent')).toBeVisible()
    expect(await within(card).findByRole('img', { name: 'Profile photo for An' })).toHaveAttribute(
      'src',
      'https://media.example.test/avatar-one',
    )
    expect(screen.getByRole('link', { name: 'Edit profile' })).toHaveAttribute(
      'href',
      '/user/profile/edit',
    )
    expect(screen.getByRole('link', { name: 'Edit interests' })).toHaveAttribute(
      'href',
      '/user/profile/edit',
    )
    expect(document.body).not.toHaveTextContent('must-never-render')
  })

  it('uses explicit empty states for missing optional fields without requesting a photo URL', async () => {
    authenticatedJson.mockImplementation(async (path) => {
      if (path === '/profile') {
        return {
          ...profile,
          full_name: null,
          display_name: null,
          student_type: null,
          nationality: null,
          major: null,
          study_year: null,
          bio: null,
          avatar: null,
          interest_ids: [],
          languages: [],
        }
      }
      return responseFor(path)
    })
    renderPage()

    const card = await screen.findByLabelText('Profile card for VGU student')
    expect(within(card).getByRole('heading', { name: 'VGU student' })).toBeVisible()
    expect(within(card).getByText('No introduction added yet.')).toBeVisible()
    expect(await within(card).findByText('No interests added yet.')).toBeVisible()
    expect(await within(card).findByText('No languages added yet.')).toBeVisible()
    expect(within(card).getAllByText('Not added')).toHaveLength(3)
    expect(authenticatedJson).not.toHaveBeenCalledWith(
      expect.stringContaining('/profile/photos/'),
      expect.anything(),
    )
  })

  it('renews a private image URL after an image load failure', async () => {
    let photoRequests = 0
    authenticatedJson.mockImplementation(async (path) => {
      if (path === `/profile/photos/${photoId}/url`) {
        photoRequests += 1
        return {
          id: photoId,
          url: `https://media.example.test/avatar-${photoRequests}`,
          expires_in: 120,
        }
      }
      return responseFor(path)
    })
    renderPage()

    const image = await screen.findByRole('img', { name: 'Profile photo for An' })
    expect(image).toHaveAttribute('src', 'https://media.example.test/avatar-1')
    fireEvent.error(image)
    await waitFor(() => expect(image).toHaveAttribute('src', 'https://media.example.test/avatar-2'))
    expect(photoRequests).toBe(2)
  })

  it('refreshes localized catalog labels while retaining stable selections', async () => {
    renderPage()
    expect(await screen.findByText('Music')).toBeVisible()
    expect(screen.getByText('English')).toBeVisible()

    await act(async () => i18n.changeLanguage('de'))

    expect(await screen.findByRole('heading', { level: 1, name: 'Mein Profil' })).toBeVisible()
    expect(await screen.findByText('Musik')).toBeVisible()
    expect(screen.getByText('Englisch')).toBeVisible()
    expect(screen.getByText('Fließend')).toBeVisible()
    expect(screen.getByText('Vollständiger Name: Nguyen Van An')).toBeVisible()
  })

  it('keeps the page recoverable when the own profile request fails', async () => {
    let attempts = 0
    authenticatedJson.mockImplementation(async (path) => {
      if (path === '/profile') {
        attempts += 1
        if (attempts <= 2) throw new ApiError(503, 'server')
      }
      return responseFor(path)
    })
    renderPage()

    expect(
      await screen.findByRole(
        'heading',
        { name: 'Your profile could not be loaded' },
        { timeout: 3000 },
      ),
    ).toBeVisible()
    fireEvent.click(screen.getByRole('button', { name: 'Try again' }))
    expect(await screen.findByLabelText('Profile card for An')).toBeVisible()
    expect(attempts).toBe(3)
  })
})
