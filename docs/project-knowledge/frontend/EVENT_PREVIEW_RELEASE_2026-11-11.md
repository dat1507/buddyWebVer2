# Event Preview isolated release — 2026-11-11

Source bf823e96b569d9b6772cb50a7a055829936915ab; baseline
f1d837be188eee878c013662c506e333ab5ce911. Candidate branch
release/user-events-preview-1x1-20261111. Exact candidate SHA is the commit containing this record.

Only runtime diff: relative aspect-square w-full shrink-0 overflow-hidden image container;
absolute inset-0 size-full object-cover object-center image. Source media untouched.
Newer main behavior retained; Pillow/Admin/Chatbot/Landing/theme unpublished commits excluded.

Verification: 41 tests across user-dashboard-events, event-detail-page, events-slider and
event-slider PASS; TypeScript via production build PASS; affected ESLint/Prettier PASS.
Build PASS with pre-existing bundle advisory. Exact locked dependencies installed in candidate.
Chrome actual component fixtures: EN/DE at 1440/768/390/320, portrait 300x900 and square 600x600;
preview widths/heights 478/350/340/270px; cover/center, no overflow; same-row cards and actions align.
Navigation/registration/detail and ongoing eligibility preserved by focused tests.
No external registration submitted or Production account used.

Safety baseline: local main 9ec31fbcf0aadfb5347bd9eba76c2f362b205904. Six dirty existing
worktrees, 227 untracked files at this preflight (three additional Chatbot docs since audit).
Hashes/status captured locally for preservation verification. Do not include unrelated work.

Production target verified: Vercel buddy-web-ver2, project prj_WZjPHgpxuEoRd393PEy8u0vt04ZX,
team team_Ll1CSfWe7u8QOjWddkuGtxXz, main/custom domain www.vgubuddyprogram.com.
Pre-release deployment dpl_GRGZ7Jfuzmhz7c7DUE7W4SLYWWro READY at baseline SHA.
API /api/health/live HTTP200 alive. No Render connector available; no backend deployment or
provider mutation performed. Post-push CI/deployment/smoke must be recorded from direct evidence;
this pre-push record does not claim Production release PASS.
