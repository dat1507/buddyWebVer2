import { Navigate, useLocation } from 'react-router'

import {
  conversationIdFromBuddyLocation,
  currentBuddiesDestination,
} from '@/features/matching/current-buddy'

function CurrentBuddyRoutePage() {
  const location = useLocation()
  const conversationId = conversationIdFromBuddyLocation(location)
  return <Navigate to={currentBuddiesDestination(conversationId)} replace />
}

export { CurrentBuddyRoutePage }
