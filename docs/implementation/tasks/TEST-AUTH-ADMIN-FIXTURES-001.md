# TEST-AUTH-ADMIN-FIXTURES-001 — Correct opt-in ADMIN fixture promotion

Status READY — FOLLOW-UP / NOT ASSIGNED. Owner requested separate follow-up2026-10-31.
test_session_csrf_live.py and test_auth_logout_live.py register a USER, then assign role=ADMIN
without clearing semester_id, violating the intended ck_users_role_semester constraint before
the ADMIN authentication assertions execute. Recovered result11 PASS/2 FAIL remains unchanged.
Scope a fixture-only correction to clear semester_id for ADMIN and retain valid USER semesters.
Keep every auth assertion and database/business constraint; verify both role variants against an
isolated disposable DB/Redis. Never use Production data. No implementation is assigned now.
Scoped UI-release exception is valid only while backend auth/models/migrations/runtime dependencies
stay identical to the deployed security baseline. Actual valid Admin API integration previously PASS.
