import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { act, cleanup, fireEvent, render, screen, within } from '@testing-library/react'
import { MemoryRouter } from 'react-router'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { profileClient } from '@/features/profile/profile-client'
import i18n from '@/i18n'
import { ApiError } from '@/lib/api'
import { UserDashboardPage } from '@/pages/user/user-dashboard-page'
import { completeProfileCompletion, incompleteProfileCompletion } from '@/test/profile-completion'
import { completeOwnProfile } from '@/test/profile'

function deferred<T>() {
  let resolve!: (value: T) => void
  const promise = new Promise<T>((done) => {
    resolve = done
  })
  return { promise, resolve }
}

describe('FE-023 profile-aware User Dashboard', () => {
  let client: QueryClient

  beforeEach(async () => {
    await i18n.changeLanguage('en')
    client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  })

  afterEach(() => {
    cleanup()
    client.clear()
    vi.restoreAllMocks()
  })

  const renderDashboard = () =>
    render(
      <QueryClientProvider client={client}>
        <MemoryRouter>
          <UserDashboardPage />
        </MemoryRouter>
      </QueryClientProvider>,
    )

  it('uses the saved own profile and links only to canonical User routes without counts', async () => {
    vi.spyOn(profileClient, 'readOwn').mockResolvedValue(completeOwnProfile)
    vi.spyOn(profileClient, 'readCompletion').mockResolvedValue(completeProfileCompletion)
    renderDashboard()

    expect(await screen.findByRole('heading', { level: 1, name: 'Dashboard' })).toBeVisible()
    expect(screen.getByText('Welcome back, An.')).toBeVisible()
    const profile = screen.getByLabelText('Profile summary for An')
    expect(within(profile).getByRole('heading', { name: 'An' })).toBeVisible()
    expect(within(profile).getByText('Vietnamese student')).toBeVisible()
    expect(within(profile).getByText('Computer Science')).toBeVisible()
    expect(within(profile).getByText('Year 3')).toBeVisible()
    expect(screen.getByRole('progressbar', { name: 'Profile completion' })).toHaveAttribute(
      'aria-valuenow',
      '100',
    )
    expect(screen.getByRole('link', { name: 'View profile' })).toHaveAttribute(
      'href',
      '/user/profile',
    )
    expect(screen.getByRole('link', { name: 'Edit profile' })).toHaveAttribute(
      'href',
      '/user/profile/edit',
    )
    expect(screen.getByRole('link', { name: 'Open matching' })).toHaveAttribute(
      'href',
      '/user/matching',
    )
    expect(screen.getByRole('link', { name: 'Explore events' })).toHaveAttribute(
      'href',
      '/user/events',
    )
    expect(
      screen.queryByText(/active matches|upcoming events|notifications/i),
    ).not.toBeInTheDocument()
  })

  it('uses the saved matching state without linking an ineligible profile into a redirect', async () => {
    vi.spyOn(profileClient, 'readOwn').mockResolvedValue({
      ...completeOwnProfile,
      matching_opt_in: false,
    })
    vi.spyOn(profileClient, 'readCompletion').mockResolvedValue({
      ...completeProfileCompletion,
      matching_eligible: false,
      reasons: ['MATCHING_OPT_IN_REQUIRED'],
    })
    renderDashboard()

    expect(
      await screen.findByText(
        'Update your matching preferences when you are ready to find a buddy.',
      ),
    ).toBeVisible()
    expect(screen.getByRole('link', { name: 'Update matching preferences' })).toHaveAttribute(
      'href',
      '/user/profile/edit',
    )
    expect(screen.queryByRole('link', { name: 'Open matching' })).not.toBeInTheDocument()
  })

  it('presents an incomplete profile as saved readiness data rather than a load failure', async () => {
    vi.spyOn(profileClient, 'readOwn').mockResolvedValue(completeOwnProfile)
    vi.spyOn(profileClient, 'readCompletion').mockResolvedValue(incompleteProfileCompletion)
    renderDashboard()

    expect(await screen.findByText('Your profile needs attention')).toBeVisible()
    expect(screen.getByText('Full name')).toBeVisible()
    expect(screen.getByText('Profile photo')).toBeVisible()
    expect(screen.getByRole('link', { name: 'Finish profile' })).toHaveAttribute(
      'href',
      '/user/profile/edit',
    )
    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
  })

  it('keeps loading neutral and exposes an explicit retry for a failed saved profile read', async () => {
    const ownProfile = deferred<typeof completeOwnProfile>()
    const readOwn = vi
      .spyOn(profileClient, 'readOwn')
      .mockReturnValueOnce(ownProfile.promise)
      .mockRejectedValueOnce(new ApiError(0, 'network'))
      .mockResolvedValueOnce(completeOwnProfile)
    vi.spyOn(profileClient, 'readCompletion').mockResolvedValue(incompleteProfileCompletion)
    const view = renderDashboard()

    expect(screen.getByRole('status')).toHaveTextContent('Loading your dashboard')
    expect(screen.queryByText('Your profile needs attention')).not.toBeInTheDocument()

    await act(async () => ownProfile.resolve(completeOwnProfile))
    expect(await screen.findByText('Your profile needs attention')).toBeVisible()
    view.unmount()
    client.clear()

    renderDashboard()
    expect(await screen.findByRole('alert')).toHaveTextContent(
      'We could not load your saved profile and readiness.',
    )
    expect(screen.queryByText('Your profile needs attention')).not.toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: 'Try again' }))
    expect(await screen.findByRole('heading', { name: 'An' })).toBeVisible()
    expect(readOwn).toHaveBeenCalledTimes(3)
  })
})
