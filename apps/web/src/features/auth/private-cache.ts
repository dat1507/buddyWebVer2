import type { Query, QueryClient } from '@tanstack/react-query'

// Future private queries use ['private', userId, ...] or meta: { private: true }.
// Recognize the profile/match/private-media roots named in AUTH-021's contract as well.
const privateRoots = new Set([
  'private',
  'profile',
  'profiles',
  'match',
  'matches',
  'matching',
  'chat',
  'private-media',
])

function isPrivateQuery(query: Query): boolean {
  return query.meta?.private === true || privateRoots.has(String(query.queryKey[0]))
}

function isChatQuery(query: Query): boolean {
  return (
    query.queryKey[0] === 'chat' ||
    (query.queryKey[0] === 'private' && query.queryKey[2] === 'chat')
  )
}

async function clearPrivateQueries(client: QueryClient): Promise<void> {
  await client.cancelQueries({ predicate: isPrivateQuery })
  client.removeQueries({ predicate: isPrivateQuery })
}

async function clearChatQueries(client: QueryClient): Promise<void> {
  await client.cancelQueries({ predicate: isChatQuery })
  client.removeQueries({ predicate: isChatQuery })
}

export { clearChatQueries, clearPrivateQueries }
