"""Original publication clock and durable permanent-eviction cleanup outbox."""

from alembic import op

revision = "0024_recap_retention"
down_revision = "0023_recaps"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Do not silently destroy pre-existing content in a schema migration. Fail closed if an
    # older backend already exceeded the new contract; reviewed reconciliation must precede it.
    op.execute("""DO $$ BEGIN
        IF (SELECT count(*) FROM app_private.recaps WHERE status='PUBLISHED' AND deleted_at IS NULL) > 10 THEN
            RAISE EXCEPTION 'Rolling 10 upgrade requires at most 10 published recaps; reconcile legacy overflow before upgrade';
        END IF; END $$""")
    op.execute("ALTER TABLE app_private.recaps ADD COLUMN first_published_at TIMESTAMPTZ")
    # Recover the earliest recorded publication; legacy rows without audit use creation time.
    op.execute("""UPDATE app_private.recaps r SET first_published_at = COALESCE(
        (SELECT min(a.created_at) FROM app_private.audit_logs a WHERE a.resource_type='recap'
        AND a.resource_id=r.id AND a.new_value->>'status'='PUBLISHED'), r.created_at)
        WHERE r.status='PUBLISHED' OR EXISTS (SELECT 1 FROM app_private.audit_logs a
        WHERE a.resource_type='recap' AND a.resource_id=r.id AND a.new_value->>'status'='PUBLISHED')""")
    op.execute("""CREATE TABLE app_private.recap_media_cleanup (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        created_at TIMESTAMPTZ NOT NULL DEFAULT now(), updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
        deleted_at TIMESTAMPTZ, recap_id UUID NOT NULL, bucket TEXT NOT NULL DEFAULT 'event-media',
        object_key TEXT NOT NULL,
        CONSTRAINT uq_recap_cleanup_key UNIQUE (object_key),
        CONSTRAINT ck_recap_cleanup_bucket CHECK (bucket='event-media'))""")
    op.execute("CREATE INDEX ix_recap_cleanup_recap ON app_private.recap_media_cleanup (recap_id)")
    op.execute(
        "CREATE INDEX ix_recaps_first_publication ON app_private.recaps (first_published_at, id) WHERE status='PUBLISHED' AND deleted_at IS NULL"
    )
    op.execute("REVOKE ALL ON app_private.recap_media_cleanup FROM PUBLIC")
    op.execute("ALTER TABLE app_private.recap_media_cleanup ENABLE ROW LEVEL SECURITY")
    op.execute(
        "GRANT SELECT,INSERT,UPDATE,DELETE ON app_private.recap_media_cleanup TO vgu_buddy_runtime"
    )
    op.execute(
        "CREATE POLICY recap_cleanup_backend ON app_private.recap_media_cleanup FOR ALL TO vgu_buddy_runtime USING(true) WITH CHECK(true)"
    )
    op.execute("""DO $$ DECLARE r text; BEGIN FOREACH r IN ARRAY ARRAY['anon','authenticated','service_role'] LOOP
        IF EXISTS(SELECT 1 FROM pg_roles WHERE rolname=r) THEN
        EXECUTE format('REVOKE ALL ON app_private.recap_media_cleanup FROM %I',r); END IF;
        END LOOP; END $$""")


def downgrade() -> None:
    # Operational rollback retains schema and pending work; downgrade is destructive, never default.
    op.execute("DROP INDEX app_private.ix_recaps_first_publication")
    op.drop_table("recap_media_cleanup", schema="app_private")
    op.execute("ALTER TABLE app_private.recaps DROP COLUMN first_published_at")
