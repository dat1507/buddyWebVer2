const UUID_PATTERN = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i
const INTERNAL_ORIGIN = 'https://email-deep-link.invalid'

const EMAIL_DESTINATIONS = Object.freeze({
  '/user/matching': 'invitation',
  '/user/buddy': 'conversation',
} as const)

type EmailDestinationPath = keyof typeof EMAIL_DESTINATIONS

function canonicalEmailReturnTo(value: unknown): string | null {
  if (
    typeof value !== 'string' ||
    !value.startsWith('/') ||
    value.startsWith('//') ||
    value.includes('\\') ||
    value.length > 256
  ) {
    return null
  }

  let parsed: URL
  try {
    parsed = new URL(value, INTERNAL_ORIGIN)
  } catch {
    return null
  }
  if (parsed.origin !== INTERNAL_ORIGIN || parsed.hash) return null
  if (!(parsed.pathname in EMAIL_DESTINATIONS)) return null

  const pathname = parsed.pathname as EmailDestinationPath
  const parameter = EMAIL_DESTINATIONS[pathname]
  const values = parsed.searchParams.getAll(parameter)
  if (values.length !== 1 || Array.from(parsed.searchParams.keys()).length !== 1) return null
  const identifier = values[0]
  if (!UUID_PATTERN.test(identifier)) return null

  const canonical = `${pathname}?${parameter}=${identifier.toLowerCase()}`
  return value === canonical ? canonical : null
}

function emailReturnToFromLoginSearch(search: string): string | null {
  const parameters = new URLSearchParams(search)
  const values = parameters.getAll('returnTo')
  if (values.length !== 1 || Array.from(parameters.keys()).length !== 1) return null
  return canonicalEmailReturnTo(values[0])
}

function emailLoginPathForLocation(location: {
  pathname: string
  search: string
  hash: string
}): string | null {
  const returnTo = canonicalEmailReturnTo(`${location.pathname}${location.search}${location.hash}`)
  return returnTo ? `/login?returnTo=${encodeURIComponent(returnTo)}` : null
}

export { canonicalEmailReturnTo, emailLoginPathForLocation, emailReturnToFromLoginSearch }
