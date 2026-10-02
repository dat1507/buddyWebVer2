# Semester database backup operations (SEM-002)

SEM-002 creates the relational half of a semester backup. It does not delete data, copy avatar
bytes, mark a backup `READY`, expire artifacts, or expose restore to an Admin/API client. SEM-003
owns avatar objects; SEM-004 owns combined verification and the `READY`/30-day lifecycle; SEM-005
and SEM-006 own reset and production restore orchestration.

## Artifact and manifest contract

The database adapter exports a single repeatable-read PostgreSQL snapshot using native binary
`COPY`. Fifteen student-owned tables are written in dependency order and packed into a deterministic
gzip/tar artifact. The export includes USER accounts, profile/photo metadata, predefined and custom
preferences, verification/refresh records, event registrations, invitations, Matches,
conversations, messages, and recipient-owned transactional outbox rows. It does not export shared
Admin, semester, interest/language/activity catalog, event/configuration, operation, or backup rows.

The separate JSON manifest is metadata, not a substitute for the PostgreSQL artifact. It records:

- manifest/artifact format versions and stable backup/semester IDs;
- server-generated creation time and source boundary time;
- the 30-day policy while leaving `expires_at` null until SEM-004 can derive it from reset
  completion;
- artifact size/SHA-256 and each table's columns, row count, byte size, SHA-256, and restore order;
- required shared semester/Admin/catalog/event references without duplicating those rows;
- source/required-target PostgreSQL major version, asyncpg producer version, and Alembic head.

Validation is fail-closed. A wrong backup ID, manifest checksum, artifact checksum/size, unexpected
or duplicate archive member, per-table checksum/size mismatch, malformed JSON, missing shared
reference, non-empty USER target, PostgreSQL-major mismatch, or Alembic-head mismatch prevents the
first restore write. Any COPY failure rolls back the complete rehearsal transaction.

## Credentials and private storage

Configure `DATABASE_BACKUP_URL` with a dedicated direct PostgreSQL role. Do not use the migration
owner, transaction pooler, browser key, or a URL in command arguments. The role needs only database
`CONNECT`, schema `USAGE`, `SELECT` on the fifteen exported `app_private` tables and `SELECT` on
`alembic_version`. The application runtime credential remains responsible only for the existing
`semester_backups` metadata update/advisory lock. All database URLs remain `SecretStr` values and
never enter the manifest, object key, command output, or logs.

The production store is the dedicated `semester-database-backups` Supabase Storage bucket. The
configuration command converges it to `public=false`, permits only JSON/gzip MIME types, uses TLS
outside localhost, disables upsert, and never creates or persists a signed/public URL. Supabase
provides provider-managed encryption at rest; account access, encryption policy, retention alarms,
and credential rotation remain operator-owned. Object keys are server-generated only:

```text
<backup UUID>/database/database-artifact-v1.tar.gz
<backup UUID>/database/database-manifest-v1.json
```

The filesystem store exists only for disposable/local acceptance. It creates a caller-supplied
private root and 0600-style files where supported, never records its host path in metadata, and must
not be used as production persistence.

## Operator commands

Create/converge the private bucket once with server-only Storage credentials:

```text
python -m app.cli configure-semester-backup-storage
```

Future reset orchestration creates the attributable `SemesterOperation` and `SemesterBackup` rows.
Given the stable UUID of a `CREATING` backup whose database fields are still empty, create its
database artifact with:

```text
python -m app.cli backup-semester-database --backup-id <UUID>
```

The command acquires a PostgreSQL advisory lock for that UUID, exports to a private temporary
directory, uploads artifact then manifest, downloads both again, validates every checksum/count
contract, and atomically records only `database_manifest_location`,
`database_manifest_checksum`, and `database_row_counts`. Its successful state remains `CREATING`;
only SEM-004 may mark the combined database/avatar backup `READY`.

If export, upload, remote read-back, or verification fails, the service deletes any uploaded partial
objects, removes temporary files, and transitions the existing backup to `FAILED` with the sanitized
`DATABASE_BACKUP_FAILED` code. It does not mutate student data. Terminal failed backups are not
silently reused.

## Acceptance and recovery

The opt-in acceptance test requires two clean loopback PostgreSQL databases named `sem002_source`
and `sem002_target`, both owned by `sem002_runner`:

```text
SEM002_SOURCE_DATABASE_URL=<direct disposable source URL>
SEM002_TARGET_DATABASE_URL=<direct disposable target URL>
python -m pytest -p no:cacheprovider tests/test_semester_database_backup_live.py -q
```

It migrates both databases, seeds representative student relationships and shared references,
backs up through the production adapter contract, restores into the second database, reconciles
rows/invariants, injects a partial-storage failure, and downgrades both databases to base. Never
point either variable at development, staging, or production. There is intentionally no production
restore CLI in SEM-002.
