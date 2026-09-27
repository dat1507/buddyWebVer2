import { describe, expect, it } from 'vitest'

import {
  MAX_CUSTOM_PREFERENCE_DISPLAY_LABEL_LENGTH,
  MAX_CUSTOM_PREFERENCE_INPUT_LENGTH,
  preferenceComparisonKey,
  preparePreferenceIdentity,
} from '@/features/profile/preference-normalization'

describe('PREF-004 client preference normalization mirror', () => {
  it.each([
    ['Photography', 'Photography', 'photography'],
    ['  Street   Photography  ', 'Street Photography', 'street photography'],
    ['Straße', 'Straße', 'strasse'],
    ['STRASSE', 'STRASSE', 'strasse'],
    ['Ｐｈｏｔｏｇｒａｐｈｙ', 'Ｐｈｏｔｏｇｒａｐｈｙ', 'photography'],
    ['oﬃce', 'oﬃce', 'office'],
    ['Tiếng\u00a0Việt', 'Tiếng Việt', 'tiếng việt'],
  ])('mirrors the published PREF-002 vectors for %s', (source, displayLabel, comparisonKey) => {
    expect(preparePreferenceIdentity(source)).toEqual({ displayLabel, comparisonKey })
  })

  it('rejects unsafe, empty and overlong display input before add', () => {
    expect(preparePreferenceIdentity(' \t ')).toBeNull()
    expect(preparePreferenceIdentity('Photo\u200bgraphy')).toBeNull()
    expect(preparePreferenceIdentity('x'.repeat(MAX_CUSTOM_PREFERENCE_INPUT_LENGTH + 1))).toBeNull()
    expect(
      preparePreferenceIdentity('x'.repeat(MAX_CUSTOM_PREFERENCE_DISPLAY_LABEL_LENGTH + 1)),
    ).toBeNull()
  })

  it('keeps semantic values distinct while matching compatibility forms', () => {
    expect(preferenceComparisonKey('Football')).not.toBe(preferenceComparisonKey('Soccer'))
    expect(preferenceComparisonKey(' photography ')).toBe(
      preferenceComparisonKey('Ｐｈｏｔｏｇｒａｐｈｙ'),
    )
  })
})
