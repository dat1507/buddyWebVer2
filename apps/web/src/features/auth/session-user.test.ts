import { describe, expect, it } from 'vitest'

import { parseSessionUser, SessionUserValidationError } from '@/features/auth/session-user'

const user = {
  id: '11111111-1111-4111-8111-111111111111',
  email: 'student@example.com',
  role: 'USER',
  email_verified: false,
}

describe('parseSessionUser', () => {
  it.each(['USER', 'ADMIN'])('accepts the sanitized backend %s DTO', (role) => {
    expect(parseSessionUser({ ...user, role })).toEqual({ ...user, role })
  })

  it.each([
    null,
    undefined,
    [],
    'credential',
    {},
    { ...user, id: 'not-a-uuid' },
    { ...user, role: 'SUPERADMIN' },
    { ...user, role: 'admin' },
    { ...user, email: '' },
    { ...user, email: 123 },
    { ...user, email_verified: 'false' },
    { ...user, email_verified: undefined },
    { user, csrf_token: 'test-only-csrf' },
  ])('rejects invalid wire data without reflecting its payload (%#)', (payload) => {
    expect(() => parseSessionUser(payload)).toThrowError(SessionUserValidationError)
    expect(() => parseSessionUser(payload)).toThrowError('Session user is invalid.')
  })

  it('copies only the allowlisted fields and prevents external user mutation', () => {
    const payload = {
      ...user,
      password: 'test-only-password',
      password_hash: 'test-only-hash',
      token: 'test-only-token',
      access_token: 'test-only-access',
      refreshToken: 'test-only-refresh',
      csrf_token: 'test-only-csrf',
      profile: { phone: 'test-only-private-phone' },
    }
    const parsed = parseSessionUser(payload)
    expect(parsed).toEqual(user)
    expect(parsed).not.toBe(payload)
    expect(Object.isFrozen(parsed)).toBe(true)
    payload.role = 'ADMIN'
    payload.email = 'changed@example.com'
    expect(parsed).toEqual(user)
    expect(() => Object.assign(parsed, { role: 'ADMIN' })).toThrowError(TypeError)
  })

  it('does not attach sensitive validation input or detailed issues to its error', () => {
    const secret = 'test-only-sensitive-input'
    try {
      parseSessionUser({ ...user, role: secret, password: secret })
      expect.fail('Expected invalid user payload to throw')
    } catch (error) {
      expect(error).toBeInstanceOf(SessionUserValidationError)
      expect(String(error)).not.toContain(secret)
      expect(JSON.stringify(error)).not.toContain(secret)
      expect(error).not.toHaveProperty('issues')
      expect(error).not.toHaveProperty('cause')
    }
  })

  it('sanitizes throwing property accessors rather than exposing their diagnostics', () => {
    const payload = Object.defineProperty({ ...user }, 'role', {
      get: () => {
        throw new Error('test-only-sensitive-accessor-diagnostics')
      },
    })
    expect(() => parseSessionUser(payload)).toThrowError(SessionUserValidationError)
    expect(() => parseSessionUser(payload)).toThrowError('Session user is invalid.')
  })
})
