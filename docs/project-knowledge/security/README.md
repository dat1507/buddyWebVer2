# Security boundaries

This describes implemented controls and recorded acceptance, not a complete security audit.
Begin with [API dependencies](../../../apps/api/app/api/dependencies.py),
[token service](../../../apps/api/app/services/tokens.py),
[CSRF](../../../apps/api/app/services/csrf.py) and
[refresh sessions](../../../apps/api/app/services/refresh_sessions.py).

| Threat / boundary             | Implemented control                                                                                | Evidence / limitation                                                                   |
| ----------------------------- | -------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------- |
| Password disclosure           | Backend bcrypt hashing, generic failures and dummy-hash verification path for unknown accounts     | Password/auth tests; no claim of an external penetration test                           |
| Script-readable credentials   | Production Secure/HttpOnly host-only access/refresh cookies; memory-only frontend identity         | Dated cookie/reload/logout checks; do not expose cookie values                          |
| Forged cross-site mutation    | Signed double-submit CSRF contract, header validation and exact-origin policy                      | CSRF tests and recorded technical acceptance                                            |
| Stolen/replayed refresh token | Server-persisted refresh families, rotation/reuse detection and revocation                         | Refresh service/API tests; expiry and logout remain server-owned                        |
| Client-side role manipulation | Persisted USER/ADMIN checks in dependencies; trusted CLI-only Admin creation                       | Role tests; route hiding alone grants no authority                                      |
| Unverified Buddy use          | Verified-current-email capability plus domain readiness                                            | Verification replay/expiry and capability tests                                         |
| IDOR / guessed UUID           | Owner/participant/role checks before private profile, invitation, conversation or media operations | Focused API negative tests; a UUID is identification, not permission                    |
| Contact/data leakage          | Safe Matching DTO, bounded private reads, no-store private responses and cache cleanup             | Schema/query/client tests; do not return raw ORM records                                |
| Private object exposure       | Private Storage, server-authorized lifecycle and bounded signed delivery                           | Media tests; signed URLs are transient access and must not be committed                 |
| WSS origin/session abuse      | Exact Origin, cookie auth, participant checks and reconnect recovery                               | Recorded WSS 101/negative coverage; do not infer all behavior from an HTTP health probe |
| Duplicate/racing state change | Transactions, participant locks, uniqueness, expected versions and idempotency                     | Acceptance, Match, chat and Event tests                                                 |
| Recovery data overwrite       | Reauth/phrase, write barrier, verified backups, monotonic new-USER restore block                   | Staging acceptance; Production backup remains failed/unverified                         |

“Same-site” and “same-origin” differ: `www` and `api` are separate origins but share the
first-party site. Credentialed CORS must still allow the exact browser origin. `SameSite=Lax`
does not replace CSRF validation. CORS governs browsers; it is not authorization against a
direct HTTP caller.

PostgreSQL migration, runtime, backup and recovery privileges are distinct. The private schema
is not an automatically public Data API. Narrow restore permissions were added in revisions
0019–0021; granting broad table ownership would weaken the intended boundary.

Invitation text is inert plain text. External Event registration URLs must satisfy the HTTPS
contract; return navigation accepts a bounded known context rather than arbitrary redirects.
Errors retain safe categories and allowlisted reasons, not submitted secrets or entire payloads.

Operational evidence: [PROD technical record](../../operations/prod-001-technical-evidence-2026-10-08.md)
and [Production status](../../implementation/production-status.md). No security gate was rerun
for this docs change. Future evidence must exclude credentials, private URLs, personal account
identifiers, signed links and raw headers/payloads; report sanitized conditions/results.
