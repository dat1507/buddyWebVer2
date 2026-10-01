import { render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes, useLocation } from 'react-router'
import { describe, expect, it } from 'vitest'

import { CurrentBuddyRoutePage } from '@/pages/user/current-buddy-route-page'
import { userNavigationItems } from '@/routes/user-navigation'
import { currentBuddyList } from '@/test/current-buddies'

function LocationProbe() {
  const location = useLocation()
  return <div data-testid="location">{location.pathname + location.search + location.hash}</div>
}

function renderRoute(entry: string) {
  render(
    <MemoryRouter initialEntries={[entry]}>
      <Routes>
        <Route path="/user/buddy" element={<CurrentBuddyRoutePage />} />
        <Route path="/user/matching" element={<LocationProbe />} />
      </Routes>
    </MemoryRouter>,
  )
}

describe('BUDDY-003 /user/buddy route compatibility', () => {
  it('keeps the existing My Buddy navigation surface available', () => {
    expect(userNavigationItems.find(({ id }) => id === 'myBuddy')).toMatchObject({
      available: true,
      to: '/user/buddy',
    })
  })

  it('redirects the existing navigation route to the canonical Current Buddies section', () => {
    renderRoute('/user/buddy')
    expect(screen.getByTestId('location')).toHaveTextContent('/user/matching#current-buddies')
  })

  it('preserves only the exact approved conversation locator', () => {
    const conversationId = currentBuddyList.items[0].conversation_id
    renderRoute(`/user/buddy?conversation=${conversationId}`)
    expect(screen.getByTestId('location')).toHaveTextContent(
      `/user/matching?conversation=${conversationId}#current-buddies`,
    )
  })

  it.each([
    '/user/buddy?conversation=not-a-uuid',
    `/user/buddy?conversation=${currentBuddyList.items[0].conversation_id}&next=https://attacker.example`,
    `/user/buddy?conversation=${currentBuddyList.items[0].conversation_id}#private`,
  ])('drops malformed or privilege-bearing route state from %s', (entry) => {
    renderRoute(entry)
    expect(screen.getByTestId('location')).toHaveTextContent('/user/matching#current-buddies')
  })
})
