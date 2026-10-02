# Semester backup verification and expiry (SEM-004)

SEM-004 combines the independently validated SEM-002 database package and SEM-003 avatar package.
It does not reset or restore student data. The reset workflow remains SEM-005 and production restore
remains SEM-006.

## Verification and retention lifecycle

Verification is deliberately two-phase because the retention contract starts at reset completion:

1. While the attributable RESET operation is `RUNNING`, `verify-semester-backup` downloads and
   fully validates the private database artifact/manifest and avatar manifest/objects. It validates
   checksums, package membership, database compatibility, source semester/boundary, backup ID,
   metadata counts, avatar identities and the cross-manifest database checksum. A successful pass
   writes the immutable server timestamp `verified_at` but leaves the backup `CREATING` with no
   expiry. SEM-005 must use that proof as its pre-delete gate.
2. After SEM-005 records the same RESET operation as `SUCCEEDED` with its authoritative database
   `completed_at` and backup ID, invoking the same command re-verifies both packages, sets
   `expires_at = operation.completed_at + 30 days`, and transitions the backup to `READY`.

Neither retry nor re-verification changes `verified_at` or `expires_at`. `FAILED` and `EXPIRED`
backups cannot return to `READY`. A missing, corrupt, mixed, stale or incompatible required package
fails closed with the sanitized `BACKUP_VERIFICATION_FAILED` metadata code; artifact locations,
checksums, bytes, credentials and signed URLs are not printed.

```text
python -m app.cli verify-semester-backup --backup-id <UUID>
```

The command reports only the stable backup ID, persisted/effective state and aggregate row/object
counts.

## Effective expiry and physical cleanup

The inclusive boundary is `server_now >= expires_at`. Backend consumers must use the shared
effective-state helper, so a stale persisted `READY` row is already unusable at the boundary even
if cleanup has not run yet.

The bounded cleanup command selects only due `READY` or `RESTORE_BLOCKED_NEW_DATA` rows in
deterministic `(expires_at, id)` order with `FOR UPDATE SKIP LOCKED`. It validates whichever strict
manifest remains after a prior partial attempt, deletes only server-generated keys beneath that
backup UUID, deletes manifests last, and persists `EXPIRED` only after cleanup succeeds. Missing
objects are idempotent. A failed partial attempt remains logically expired and can be retried while
unrelated storage objects remain untouched.

```text
python -m app.cli expire-semester-backups --batch-size 20
```

The supported batch range is 1–100. The command emits aggregate selected/expired/cleaned/failed
counts and returns non-zero if any selected backup failed cleanup. Invoke it from the existing
OPS-001 scheduler/operational environment; SEM-004 does not provision a new worker or paid service.

## Private-storage boundary

All reads and deletes use server credentials against the private `semester-database-backups`
bucket. No browser client, public URL or signed URL participates. Cleanup never lists or deletes a
broad bucket prefix: database keys are fixed by contract and avatar keys are reconstructed only
from a checksum-validated manifest linked to the persisted backup metadata.
