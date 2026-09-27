const MAX_CUSTOM_PREFERENCE_INPUT_LENGTH = 255
const MAX_CUSTOM_PREFERENCE_DISPLAY_LABEL_LENGTH = 120
const MAX_CUSTOM_PREFERENCE_KEY_LENGTH = 255

const unsafeControlPattern = /[\p{Cc}\p{Cf}\p{Cs}]/u

interface ClientPreferenceIdentity {
  displayLabel: string
  comparisonKey: string
}

function codePointLength(value: string): number {
  return Array.from(value).length
}

function collapseWhitespace(value: string): string {
  return value.trim().replace(/\s+/gu, ' ')
}

function containsUnsafeControl(value: string): boolean {
  return Array.from(value).some(
    (character) => character !== '\t' && unsafeControlPattern.test(character),
  )
}

function clientCasefold(value: string): string {
  // JavaScript has no native Unicode casefold. These mappings cover the PREF-002
  // golden vectors; the server remains authoritative for the complete Unicode table.
  return value.toLowerCase().replaceAll('ß', 'ss').replaceAll('ς', 'σ')
}

function preparePreferenceIdentity(value: string): ClientPreferenceIdentity | null {
  if (codePointLength(value) > MAX_CUSTOM_PREFERENCE_INPUT_LENGTH || containsUnsafeControl(value)) {
    return null
  }

  const displayLabel = collapseWhitespace(value)
  if (
    !displayLabel ||
    codePointLength(displayLabel) > MAX_CUSTOM_PREFERENCE_DISPLAY_LABEL_LENGTH ||
    containsUnsafeControl(displayLabel)
  ) {
    return null
  }

  const comparisonKey = clientCasefold(collapseWhitespace(value.normalize('NFKC')))
  if (
    !comparisonKey ||
    codePointLength(comparisonKey) > MAX_CUSTOM_PREFERENCE_KEY_LENGTH ||
    containsUnsafeControl(comparisonKey)
  ) {
    return null
  }

  return { displayLabel, comparisonKey }
}

function preferenceComparisonKey(value: string): string | null {
  return preparePreferenceIdentity(value)?.comparisonKey ?? null
}

export {
  MAX_CUSTOM_PREFERENCE_DISPLAY_LABEL_LENGTH,
  MAX_CUSTOM_PREFERENCE_INPUT_LENGTH,
  preferenceComparisonKey,
  preparePreferenceIdentity,
}
export type { ClientPreferenceIdentity }
