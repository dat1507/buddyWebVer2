# Supabase Free off-site disaster recovery plan

This plan covers the complete BuddyWebv2 application state that is not reproducible from source:

- every object and row in the application-owned `app_private` PostgreSQL schema;
- the exact Alembic revision and application commit associated with the snapshot;
- every object in the private `profile-images` and `semester-database-backups` buckets;
- a redacted inventory, byte counts and SHA-256 checksums.

It deliberately excludes provider-managed Supabase schemas, Upstash ephemeral Pub/Sub state,
secrets, passwords, signed URLs and Resend provider history. Database roles, Vault/Cron entries,
buckets and service configuration are reconstructed from reviewed migrations/runbooks with newly
generated credentials.

This is a prepared plan, not a claim that an off-site backup or restore rehearsal has occurred.
No database, bucket, S3 key, off-site account, or scheduled runner was created during preparation.

## Credential model

`DATABASE_BACKUP_URL` is **not** the credential for this job. Its committed contract is limited to
the fifteen semester-restorable student tables plus `alembic_version`; it intentionally omits
shared Admin, catalog, event, semester and operation data. Higher privilege does not make a
credential suitable for a different purpose.

Create a distinct `vgu_buddy_dr_backup` PostgreSQL login only after review. It needs direct/session
pooler connectivity, database CONNECT, schema USAGE, SELECT on every `app_private` table and
sequence, and SELECT on `public.alembic_version`. It must have no INSERT/UPDATE/DELETE/DDL,
CREATEDB, CREATEROLE, replication, role membership, or migration ownership. Grant matching default
read privileges for future objects owned by the migration role. Before approval, query
`pg_class.relrowsecurity`; if any selected table has RLS, stop and review a narrowly scoped
`BYPASSRLS` decision rather than producing a silently partial dump with `--enable-row-security`.

Keep this credential local to the backup operator/runner. Do not add it to the FastAPI, Render,
Cloud Run, Vercel, Supabase Edge, GitHub, or tracked `.env` configuration. Obtain a session-pooler
host/port/user from **Supabase Dashboard -> Connect** when local IPv6 cannot reach the direct host.
Do not use the runtime role, migration owner, `postgres`, or the semester backup role.

Storage export uses a separate server-only Supabase S3 access key. Supabase documents that this key
bypasses RLS and can access all buckets, so it belongs only in an OS credential store or an
interactive S3-client profile. It must never appear in a command argument, repository, CI log,
manifest, or chat. Rotate/revoke it after the workflow is validated, and after any suspected
operator-device exposure.

## Logical database capture

Use PostgreSQL client tools at the same major version as, or newer than, the source server. The
password is entered at the interactive `-W` prompt, so it is absent from PowerShell history:

```powershell
$env:PGHOST = '<session-pooler-or-direct-host>'
$env:PGPORT = '<5432-session-pooler-or-direct-port>'
$env:PGDATABASE = 'postgres'
$env:PGUSER = '<dedicated-dr-backup-user>'
$env:PGSSLMODE = 'require'

pg_dump -W --format=custom --no-owner --schema=app_private `
  --strict-names --lock-wait-timeout=60000 `
  --file='<private-output>\app-private.dump'

psql -W --no-psqlrc --tuples-only --no-align `
  --command='SELECT version_num FROM public.alembic_version' `
  --output='<private-output>\alembic-version.txt'

pg_restore --list '<private-output>\app-private.dump' `
  | Set-Content -Encoding utf8 '<private-output>\database-inventory.txt'
Get-FileHash -Algorithm SHA256 '<private-output>\app-private.dump'
```

`<private-output>` must be a new timestamped directory on an encrypted local volume with
operator-only ACLs. Stop on any `pg_dump` warning or non-zero exit. Record the tool/server versions,
UTC snapshot time, dump byte size/hash, `alembic-version.txt`, immutable Git commit and aggregate
table row counts in a manifest. Never record connection strings or row content.

The schema archive intentionally retains ACL statements while suppressing source ownership. The
restore rehearsal must prove those ACLs can be applied to newly created, password-rotated role
names. If provider ownership/default-privilege statements are not portable, replace them with a
reviewed declarative permission script before production; do not edit a live database ad hoc.

## Storage capture

In **Supabase Dashboard -> Storage -> Configuration -> S3**, an authorized operator may enable S3
and generate server-only credentials. Configure an S3-compatible client such as rclone or
Cyberduck interactively from the shown endpoint, region, access key and secret. Use the direct
`https://<project-ref>.storage.supabase.co/storage/v1/s3` endpoint documented by Supabase.

Use a non-destructive **copy/download** into the same timestamped private directory; never use
`sync`, `move`, or delete against the source:

```text
storage/profile-images/<exact object keys>
storage/semester-database-backups/<exact object keys>
```

Generate an inventory containing bucket, object key, byte size, MIME/content type and local
SHA-256. It must contain no signed URL or credential. Reconcile object count/bytes against a
read-only source listing. Supabase Storage has no S3 object versioning; a deleted object cannot be
recovered unless this independent copy exists.

## Encryption and off-site retention

Before upload, encrypt the complete database dump, storage objects and manifest with an audited
tool (for example age or 7-Zip AES-256) using a recovery key stored outside the operator laptop.
Upload only encrypted artifacts to an existing zero-cost institutional OneDrive/Google Drive or
another owner-approved off-site quota. Do not use Git/GitHub, a public bucket, a shared link, or the
same Supabase project as the only off-site copy.

Keep at minimum:

- the latest four weekly verified snapshots;
- one monthly snapshot for three months;
- an additional snapshot before every migration, semester reset, credential/role redesign, or
  provider cutover.

Deletion/retention automation is not authorized until the exact off-site target and prefix have
been validated. Prefer provider versioning/trash; never run a recursive delete against an
unresolved variable or broad drive root.

## Restore rehearsal

At least quarterly and before production approval, restore into a new disposable compatible
Supabase project/database and a new private Storage namespace. Never restore over staging or
production.

1. Verify the encrypted archive, manifest, SHA-256 values, byte/object/table counts and source
   revision before opening a database connection.
2. Create required extensions and fresh login roles with new passwords; never restore passwords.
3. Inspect the archive with `pg_restore --list`. Treat dump contents as executable database code.
4. Restore `app_private` using `pg_restore --exit-on-error --single-transaction --no-owner` as the
   authorized target owner. Reconcile every table count and application invariant.
5. Prove the physical schema matches the recorded Alembic revision. Only after that proof may
   `alembic stamp <recorded-revision>` reconstruct the missing `public.alembic_version` marker;
   never update that table manually or stamp around a mismatch. Run `alembic upgrade head` only if
   the target intentionally moves to a later reviewed revision.
6. Recreate the private buckets, then upload to the exact keys with recorded MIME types. Reconcile
   every object hash and confirm anonymous/public reads fail.
7. Recreate Vault/Cron, API provider configuration and Redis namespaces from runbooks with new
   secrets. Do not copy Vault ciphertext or Redis transient state.
8. Run readiness, auth, profile/avatar, matching, invitation, chat, email, Admin and Semester
   read-only/safe smoke tests. Record RPO/RTO and sanitized PASS/FAIL evidence.
9. Destroy the disposable target only after evidence is captured and the exact target identity is
   rechecked.

Any schema/ACL failure, missing object, checksum/count mismatch or stale revision fails the
rehearsal closed. Repair the export/permission procedure and produce a new backup; do not weaken
verification or merge a partial restore with a live cohort.

## Automation and production gate

Supabase Cron cannot perform a full `pg_dump` plus independent Storage/off-site export. A free
workflow therefore needs either a trusted always-available local runner or another explicitly
approved secret-bearing runner. GitHub Actions is not the default because it spreads database and
full Storage credentials into another provider. Until a runner and off-site destination are chosen,
the safe interim is a manual weekly capture plus mandatory pre-change capture.

Production is not DR-ready until one complete encrypted off-site snapshot and one disposable
restore rehearsal pass, the operator can recover the encryption key, and a named owner accepts the
measured RPO/RTO. Supabase Free limits and lack of PITR make this an operational release gate, not
documentation-only evidence.

## References

- [Supabase backup/restore with CLI](https://supabase.com/docs/guides/platform/migrating-within-supabase/backup-restore)
- [Supabase Storage S3 authentication](https://supabase.com/docs/guides/storage/s3/authentication)
- [Supabase Storage bulk download](https://supabase.com/docs/guides/storage/management/download-objects)
- [Supabase S3 compatibility and no object versioning](https://supabase.com/docs/guides/storage/s3/compatibility)
- [PostgreSQL pg_dump](https://www.postgresql.org/docs/current/app-pgdump.html)
