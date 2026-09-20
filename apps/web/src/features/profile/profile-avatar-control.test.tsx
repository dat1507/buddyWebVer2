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
const profileId = 'bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb'
const oldPhotoId = 'cccccccc-cccc-4ccc-8ccc-cccccccccccc'
const newPhotoId = 'dddddddd-dddd-4ddd-8ddd-dddddddddddd'

const oldPhoto = {
  id: oldPhotoId,
  mime_type: 'image/jpeg',
  byte_size: 12_345,
  width: 600,
  height: 600,
  processing_status: 'READY' as const,
  created_at: '2026-09-20T08:00:00Z',
}
const newPhoto = {
  ...oldPhoto,
  id: newPhotoId,
  mime_type: 'image/png',
  byte_size: 23_456,
  created_at: '2026-09-20T09:00:00Z',
}
const profile = {
  id: profileId,
  full_name: 'Nguyen Van An',
  display_name: 'An',
  student_type: 'VIETNAMESE' as const,
  nationality: 'Vietnamese',
  major: 'Computer Science',
  study_year: 3,
  bio: 'Hello',
  avatar: oldPhoto,
  interest_ids: [],
  languages: [],
  version: 4,
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

describe('FE-039 reusable profile avatar control', () => {
  let authenticatedJson: MockInstance<typeof sessionClient.authenticatedJson>
  let createObjectURL: ReturnType<typeof vi.fn>
  let revokeObjectURL: ReturnType<typeof vi.fn>

  beforeEach(async () => {
    await i18n.changeLanguage('en')
    queryClient.clear()
    useAuthStore.getState().setAuthenticated(user)
    createObjectURL = vi.fn()
    revokeObjectURL = vi.fn()
    const NativeURL = globalThis.URL
    class TestURL extends NativeURL {
      static createObjectURL(object: Blob | MediaSource): string {
        return (createObjectURL as unknown as (value: Blob | MediaSource) => string)(object)
      }

      static revokeObjectURL(url: string): void {
        ;(revokeObjectURL as unknown as (value: string) => void)(url)
      }
    }
    vi.stubGlobal('URL', TestURL)
    authenticatedJson = vi.spyOn(sessionClient, 'authenticatedJson')
  })

  afterEach(() => {
    cleanup()
    queryClient.clear()
    useAuthStore.getState().resetSession()
    vi.restoreAllMocks()
    vi.unstubAllGlobals()
  })

  it('keeps the saved avatar after a failed upload and retries the same accessible preview', async () => {
    const replacement = new File(['replacement'], 'replacement.png', { type: 'image/png' })
    let profileReads = 0
    let uploadAttempts = 0
    createObjectURL.mockReturnValue('blob:replacement')
    authenticatedJson.mockImplementation(async (path, options) => {
      if (path === '/profile') {
        profileReads += 1
        return profileReads === 1 ? profile : { ...profile, avatar: newPhoto }
      }
      if (path === `/profile/photos/${oldPhotoId}/url`) {
        return { id: oldPhotoId, url: 'https://media.example.test/old', expires_in: 300 }
      }
      if (path === `/profile/photos/${newPhotoId}/url`) {
        return { id: newPhotoId, url: 'https://media.example.test/new', expires_in: 300 }
      }
      if (path === '/profile/photos' && options?.method === 'POST') {
        uploadAttempts += 1
        if (uploadAttempts === 1) throw new ApiError(503, 'server')
        return {
          ...newPhoto,
          bucket: 'must-never-reach-the-ui',
          object_key: 'must-never-reach-the-ui',
        }
      }
      throw new Error(`Unexpected test path: ${path}`)
    })
    const invalidateQueries = vi.spyOn(queryClient, 'invalidateQueries')
    renderPage()

    expect(await screen.findByRole('img', { name: 'Current profile photo' })).toHaveAttribute(
      'src',
      'https://media.example.test/old',
    )
    const input = screen.getByLabelText('Choose a replacement photo')
    expect(input).toHaveAttribute('accept', 'image/jpeg,image/png,image/webp')
    input.focus()
    expect(input).toHaveFocus()
    fireEvent.change(input, { target: { files: [replacement] } })
    expect(
      await screen.findByRole('img', { name: 'Preview of selected profile photo' }),
    ).toHaveAttribute('src', 'blob:replacement')

    fireEvent.click(screen.getByRole('button', { name: 'Upload photo' }))

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'The saved photo is unchanged; try again.',
    )
    expect(screen.getByRole('img', { name: 'Current profile photo' })).toHaveAttribute(
      'src',
      'https://media.example.test/old',
    )
    expect(screen.getByRole('img', { name: 'Preview of selected profile photo' })).toBeVisible()
    fireEvent.click(screen.getByRole('button', { name: 'Retry upload' }))

    expect(await screen.findByText('Profile photo updated.')).toBeVisible()
    expect(await screen.findByRole('img', { name: 'Current profile photo' })).toHaveAttribute(
      'src',
      'https://media.example.test/new',
    )
    expect(authenticatedJson).toHaveBeenCalledWith('/profile/photos', {
      method: 'POST',
      binaryBody: replacement,
      contentType: 'image/png',
    })
    expect(invalidateQueries).toHaveBeenCalledWith({
      queryKey: ['profile', 'completion'],
    })
    expect(document.body).not.toHaveTextContent('must-never-reach-the-ui')
    expect(revokeObjectURL).toHaveBeenCalledWith('blob:replacement')
  })

  it('preserves the current avatar when removal fails and removes it after retry', async () => {
    let profileReads = 0
    let removeAttempts = 0
    authenticatedJson.mockImplementation(async (path, options) => {
      if (path === '/profile') {
        profileReads += 1
        return profileReads === 1 ? profile : { ...profile, avatar: null }
      }
      if (path === `/profile/photos/${oldPhotoId}/url`) {
        return { id: oldPhotoId, url: 'https://media.example.test/old', expires_in: 300 }
      }
      if (path === `/profile/photos/${oldPhotoId}` && options?.method === 'DELETE') {
        removeAttempts += 1
        if (removeAttempts === 1) throw new ApiError(503, 'server')
        return undefined
      }
      throw new Error(`Unexpected test path: ${path}`)
    })
    const invalidateQueries = vi.spyOn(queryClient, 'invalidateQueries')
    renderPage()
    expect(await screen.findByRole('img', { name: 'Current profile photo' })).toBeVisible()

    fireEvent.click(screen.getByRole('button', { name: 'Remove current photo' }))
    expect(screen.getByRole('alertdialog', { name: 'Remove profile photo?' })).toBeVisible()
    fireEvent.click(screen.getByRole('button', { name: 'Remove photo' }))

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Your saved photo could not be removed.',
    )
    expect(screen.getByAltText('Current profile photo')).toBeVisible()
    fireEvent.click(screen.getByRole('button', { name: 'Remove photo' }))

    expect(await screen.findByText('Profile photo removed.')).toBeVisible()
    expect(screen.getByRole('img', { name: 'No profile photo saved' })).toBeVisible()
    expect(screen.queryByRole('button', { name: 'Remove current photo' })).not.toBeInTheDocument()
    expect(authenticatedJson).toHaveBeenCalledWith(`/profile/photos/${oldPhotoId}`, {
      method: 'DELETE',
    })
    expect(invalidateQueries).toHaveBeenCalledWith({
      queryKey: ['profile', 'completion'],
    })
  })

  it('revokes local preview URLs when a selection changes and when the control unmounts', async () => {
    authenticatedJson.mockImplementation(async (path) => {
      if (path === '/profile') return { ...profile, avatar: null }
      throw new Error(`Unexpected test path: ${path}`)
    })
    createObjectURL.mockReturnValueOnce('blob:first').mockReturnValueOnce('blob:second')
    const view = renderPage()
    const input = await screen.findByLabelText('Choose a profile photo')
    const first = new File(['first'], 'first.webp', { type: 'image/webp' })
    const second = new File(['second'], 'second.jpeg', { type: 'image/jpeg' })

    fireEvent.change(input, { target: { files: [first] } })
    expect(
      await screen.findByRole('img', { name: 'Preview of selected profile photo' }),
    ).toHaveAttribute('src', 'blob:first')
    fireEvent.change(input, { target: { files: [second] } })
    await waitFor(() => expect(revokeObjectURL).toHaveBeenCalledWith('blob:first'))
    expect(screen.getByRole('img', { name: 'Preview of selected profile photo' })).toHaveAttribute(
      'src',
      'blob:second',
    )

    view.unmount()
    expect(revokeObjectURL).toHaveBeenCalledWith('blob:second')
  })

  it('localizes the reusable file and action labels in German', async () => {
    await i18n.changeLanguage('de')
    authenticatedJson.mockImplementation(async (path) => {
      if (path === '/profile') return { ...profile, avatar: null }
      throw new Error(`Unexpected test path: ${path}`)
    })
    renderPage()

    expect(await screen.findByRole('heading', { name: 'Profilfoto' })).toBeVisible()
    expect(screen.getByLabelText('Profilfoto auswählen')).toBeVisible()
    expect(screen.getByRole('button', { name: 'Foto hochladen' })).toBeDisabled()
  })
})
