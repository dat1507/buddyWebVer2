import { z } from 'zod'

const sessionUserSchema = z
  .object({
    id: z.string().uuid(),
    email: z.string().min(1),
    role: z.enum(['USER', 'ADMIN']),
    email_verified: z.boolean(),
    email_verified_at: z
      .string()
      .datetime({ offset: true })
      .nullable()
      .optional()
      .transform((value) => value ?? null),
  })
  .superRefine((user, context) => {
    if (user.role === 'USER' && user.email_verified !== Boolean(user.email_verified_at)) {
      context.addIssue({ code: 'custom', path: ['email_verified'], message: 'Invalid state.' })
    }
  })

type SessionUser = Readonly<z.infer<typeof sessionUserSchema>>
type UserRole = SessionUser['role']

class SessionUserValidationError extends Error {
  constructor() {
    super('Session user is invalid.')
    this.name = 'SessionUserValidationError'
  }
}

function parseSessionUser(payload: unknown): SessionUser {
  try {
    const result = sessionUserSchema.safeParse(payload)
    if (result.success) {
      // Zod strips unknown fields and creates a copy; freeze the scalar presentation fields.
      return Object.freeze(result.data)
    }
  } catch {
    // Also sanitize non-JSON inputs whose property accessors throw sensitive diagnostics.
  }
  // Never retain or surface raw API payloads/Zod issues, which may contain credentials.
  throw new SessionUserValidationError()
}

export { parseSessionUser, SessionUserValidationError }
export type { SessionUser, UserRole }
