export const MIN_REGISTRATION_PASSWORD_CHARACTERS = 8
export const BCRYPT_MAX_PASSWORD_BYTES = 72

export function registrationPasswordUtf8Bytes(password: string) {
  return new TextEncoder().encode(password).length
}
