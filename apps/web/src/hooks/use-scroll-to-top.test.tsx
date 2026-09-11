import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { Link, MemoryRouter, useLocation } from 'react-router'
import { describe, expect, it, vi } from 'vitest'

import { useScrollToTop } from '@/hooks/use-scroll-to-top'

const publicRoutes = ['/login', '/register', '/adminLogin'] as const

function ScrollToTopHarness() {
  const location = useLocation()
  useScrollToTop()

  return (
    <>
      <p data-testid="current-location">{`${location.pathname}${location.hash}`}</p>
      {publicRoutes.map((route) => (
        <Link key={route} to={route}>
          {route}
        </Link>
      ))}
      <Link to="/login#form">Login form anchor</Link>
    </>
  )
}

describe('useScrollToTop', () => {
  it.each(publicRoutes)('scrolls to the top when navigating to %s', async (route) => {
    const scrollTo = vi.mocked(window.scrollTo)
    render(
      <MemoryRouter initialEntries={['/']}>
        <ScrollToTopHarness />
      </MemoryRouter>,
    )
    await waitFor(() => expect(scrollTo).toHaveBeenCalledTimes(1))
    scrollTo.mockClear()

    fireEvent.click(screen.getByRole('link', { name: route }))

    await waitFor(() => expect(scrollTo).toHaveBeenCalledWith(0, 0))
    expect(screen.getByTestId('current-location')).toHaveTextContent(route)
  })

  it('does not override hash-only navigation within the current route', async () => {
    const scrollTo = vi.mocked(window.scrollTo)
    render(
      <MemoryRouter initialEntries={['/login']}>
        <ScrollToTopHarness />
      </MemoryRouter>,
    )
    await waitFor(() => expect(scrollTo).toHaveBeenCalledTimes(1))
    scrollTo.mockClear()

    fireEvent.click(screen.getByRole('link', { name: 'Login form anchor' }))

    expect(screen.getByTestId('current-location')).toHaveTextContent('/login#form')
    expect(scrollTo).not.toHaveBeenCalled()
  })
})
