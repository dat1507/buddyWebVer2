# Expired Buddy-message cleanup

CHAT-005 physically removes messages after the retention deadline already persisted in
`app_private.buddy_messages.expires_at`. History and realtime reads continue to exclude expired rows
even when physical cleanup is delayed.

## Entrypoint and scheduler boundary

Run one bounded batch with:

```text
python -m app.cli cleanup-expired-chat-messages --batch-size 20
```

The default is 20 and the accepted range is 1–100. One command invocation processes one batch and
exits successfully when it deletes zero rows. An external deployment scheduler may repeat the
command until a run reports fewer deleted rows than the requested batch size. CHAT-005 does not add
a second scheduler or alter the existing Supabase Cron → Edge email path; deployment owns cadence.

## Database and concurrency contract

The command uses the runtime database session and a narrowly granted PostgreSQL function. Runtime
has no direct table-level DELETE privilege. The function:

- captures PostgreSQL `statement_timestamp()` unless a non-future test instant is supplied;
- selects only rows with persisted `expires_at <= cleanup_now`;
- orders by `expires_at ASC, id ASC`;
- locks at most the requested batch with `FOR UPDATE SKIP LOCKED`;
- hard-deletes only those message rows in the same short transaction.

Overlapping workers skip each other's locked rows and make forward progress. A failed transaction
rolls back the whole batch; a retry safely resumes. Deleting a message cannot cascade upward to its
conversation, Match, invitation, user or profile. The job makes no Redis, email, storage or network
call while holding locks.

## Telemetry and failure handling

Success emits only batch size, selected/deleted counts and duration. Failure adds the exception type
and the CLI returns a stable sanitized error. Never attach message bodies, message/conversation IDs,
participant identifiers, email addresses, credentials or database URLs to cleanup logs or evidence.

Alert when the command repeatedly fails or full batches persist across scheduled runs. Verify API
history still hides expired rows before investigating job lag; do not restore expired rows or
recompute expiry from `created_at` or `read_at`.
