# Progressive study guide

Use one workflow at a time. For each stage, explain the idea aloud, trace its source path,
then inspect a focused test and a historical change. You do not need to read every task extract.

## Level 1 — Fundamentals

| Concept                      | Plain explanation                                                                           | BuddyWeb exercise                                                                                                      |
| ---------------------------- | ------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------- |
| Frontend/backend             | Frontend renders what a person sees; backend enforces shared rules and data access          | Open App.tsx and main.py using the [architecture links](../ARCHITECTURE.md); identify one public and one private route |
| HTTP/REST                    | A request has a method/path, headers and sometimes a body; a response has a status and data | Trace GET recommendations; explain why GET should not create a Match and why Accept is POST                            |
| SQL/database                 | Tables hold related facts; keys connect rows, constraints reject invalid facts              | Draw user → profile and invitation → Match → conversation from [database guide](../database/README.md)                 |
| Authentication/authorization | Proving identity differs from deciding permission                                           | Explain why a logged-in USER still cannot administer Events                                                            |
| Git                          | Commits record snapshots/diffs; ancestry shows what changes a later snapshot contains       | Compare `git show --stat 65364a1` with its task; distinguish commit from deployment                                    |
| Deployment                   | A host runs/builds a particular version with its environment configuration                  | Explain why changing a local VITE flag does not change an already-built public site                                    |

Useful status meanings: 401 lacks valid authentication; 403 denies permission; 404 does not
expose an accessible resource; 409 conflicts with current state/version; 422 rejects request
shape; 429 limits request rate; 503 indicates unavailable required capability/dependency.
Exact route contracts still matter: a 404 alone is not a diagnosis.

## Level 2 — Technology stack

React builds reusable UI components. TypeScript catches shape/type mistakes before running.
Vite bundles browser assets. React Router maps URLs to screens. Tailwind expresses layout/style
utilities, while shared UI components avoid duplicating behavior. i18next selects EN/DE text.

TanStack Query manages fetched server data and cache invalidation; Zustand holds small in-memory
session state. Neither is the durable database. FastAPI maps HTTP to typed Python handlers;
Pydantic validates contracts; SQLAlchemy maps/query-builds relational data; asyncpg carries
asynchronous PostgreSQL operations. Alembic versions database changes.

PostgreSQL owns durable constraints/transactions. Redis supports shared limits and realtime
distribution. Supabase hosts DB/private Storage/Edge scheduling; Resend delivers email.
Vercel hosts the browser build; Render runs the API container. Docker makes local services
reproducible. Technology benefits explain how the code works; original personal selection
motives must not be invented. See [decisions](../decisions/README.md).

## Level 3 — Trace real implementation

1. Follow [registration/profile](../WORKFLOWS.md): locate the owner check, version conflict,
   verified-email boundary and avatar metadata. Explain a failure without exposing private data.
2. Work the score example by hand, then read `score_eligible_pair`. Change only an imagined
   input and predict which weights contribute; no code modification is needed.
3. Trace invitation Accept through participant locks, Match creation, conversation and outbox.
   Ask which records would be inconsistent if committed separately.
4. Trace chat send/retry/reconnect. Identify the idempotency key and the authoritative history.
5. Trace Event Admin update → canonical record → slider DTO → common hook → Landing/User cards.
   Explain optional registration and why stored MEMBERS no longer means private publication.
6. Read Semester management and the failed-backup incident. Explain why a healthy API must not
   enable destructive recovery without verified artifacts.

## Level 4 — Engineering problems

Read [incidents](../incidents/README.md). For each case, write five sentences: symptom,
evidence, cause confidence, resolution, verification. Compare a test-harness race, an image
transition defect, a content-consistency release failure and an unresolved backup failure.
They require different debugging methods and different claims of success.

Practice evidence distinctions: “the code implements”, “the focused tests recorded”,
“the operator observed on this date” and “this remains unknown”. This is essential engineering
communication, especially when the README and historical status disagree.

## Level 5 — Interview preparation

Use [the interview guide](INTERVIEW_GUIDE.md). Prepare a two-minute architecture explanation,
one end-to-end feature walkthrough, one race/integrity example and one debugging story with
an honest limitation. Use “the project implements” unless you can substantiate personal work.
For personal contribution claims, inspect the diff and explain the exact change yourself;
commit authorship alone is insufficient proof of independent design or implementation.

## Suggested first study session

Read architecture, then Matching workflow and its scoring test. Calculate 67.5 → 68 by hand.
Explain why eligibility precedes scoring and why a recommendation read creates nothing.
Then answer interview questions 1, 3 and 7 without looking at the model answers.
