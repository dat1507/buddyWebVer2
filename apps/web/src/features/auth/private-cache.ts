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
  'private-media',
])

function isPrivateQuery(query: Query): boolean {
  return query.meta?.private === true || privateRoots.has(String(query.queryKey[0]))
}

async function clearPrivateQueries(client: QueryClient): Promise<void> {
  await client.cancelQueries({ predicate: isPrivateQuery })
  client.removeQueries({ predicate: isPrivateQuery })
}

export { clearPrivateQueries }
