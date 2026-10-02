# Semester avatar backups (SEM-003)

SEM-003 copies only private profile-image objects referenced by the exact `profile_photos`
snapshot recorded in the SEM-002 database manifest. It never lists a bucket to infer ownership, so
orphan, event, slider, and foreign objects are outside the backup scope.

## Private object layout

All objects use the existing private `semester-database-backups` bucket and server-generated keys:

- `<backup UUID>/avatars/objects/<photo UUID>.<jpg|png|webp>`
- `<backup UUID>/avatars/avatar-manifest-v1.json`

Uploads use `x-upsert: false`. The bucket remains private and allows only gzip, JSON, JPEG, PNG,
and WebP. Manifest locations are backend-only `supabase-storage://` identities; signed or public
URLs are never persisted.

## Manifest and integrity

The strict manifest binds the avatar package to the SEM-002 database-manifest checksum and source
semester boundary. Each object records opaque photo/profile/owner UUIDs, its original managed
profile-image key, backup key, MIME type, dimensions, byte size, and SHA-256 checksum. Entries are
sorted by photo UUID. Duplicate identities, unexpected/missing members, path traversal, invalid
managed keys, metadata mismatches, corrupt image bytes, size mismatches, and checksum mismatches
all fail closed.

A database row that references a missing or invalid object fails the whole avatar backup. A profile
with no photo needs no object. Unreferenced bucket objects are intentionally ignored.

## Operator flow

1. Run `backup-semester-database --backup-id <UUID>` for the existing `CREATING` backup.
2. Run `backup-semester-avatars --backup-id <UUID>` with server-only runtime database and Storage
   credentials.
3. Treat the command output as aggregate-only evidence. It reports object count, total bytes, and
   state, but never keys, signed URLs, checksums, owner data, credentials, or image content.

The avatar command downloads private source objects directly with authenticated server requests,
uploads to the private backup prefix without overwrite, downloads every backup object again, and
verifies the full package before atomically attaching avatar manifest metadata. Partial uploads are
deleted. A successful SEM-003 run deliberately leaves the backup in `CREATING`; SEM-004 owns the
combined database/avatar verification, `READY`, retention timestamp, and expiry behavior.

## Restore boundary

SEM-003 includes an adapter-level rehearsal helper. It validates the complete package before any
target write, recreates the exact managed profile-image keys with non-upsert uploads, and removes
only objects created by that attempt if a later upload fails. Existing target collisions fail and
are never overwritten. SEM-006 remains the owner of production database/object restore
orchestration and mapping reconciliation.
