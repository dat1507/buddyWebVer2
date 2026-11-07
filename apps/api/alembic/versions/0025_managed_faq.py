"""Private, versioned chatbot FAQ management."""

from alembic import op

revision = "0025_managed_faq"
down_revision = "0024_recap_retention"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""CREATE TABLE app_private.managed_faq (
        id UUID PRIMARY KEY,
        builtin_id TEXT UNIQUE CHECK (length(builtin_id) <= 80),
        version INTEGER NOT NULL CHECK (version > 0),
        draft_revision INTEGER NOT NULL CHECK (draft_revision BETWEEN 1 AND version),
        published_revision INTEGER CHECK (published_revision BETWEEN 1 AND version),
        published_by UUID REFERENCES app_private.users(id),
        published_at TIMESTAMPTZ,
        CHECK ((published_by IS NULL) = (published_at IS NULL)),
        CHECK (published_revision IS NULL OR published_at IS NOT NULL),
        created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
        updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
    )""")
    op.execute("""CREATE TABLE app_private.managed_faq_revision (
        faq_id UUID NOT NULL REFERENCES app_private.managed_faq(id),
        revision INTEGER NOT NULL CHECK (revision > 0),
        author_id UUID NOT NULL REFERENCES app_private.users(id),
        content JSONB NOT NULL CHECK (jsonb_typeof(content) = 'object'),
        created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
        PRIMARY KEY (faq_id, revision)
    )""")
    for pointer in ("draft_revision", "published_revision"):
        op.execute(f"""ALTER TABLE app_private.managed_faq ADD CONSTRAINT fk_managed_{pointer}
            FOREIGN KEY (id, {pointer}) REFERENCES app_private.managed_faq_revision(faq_id, revision)
            DEFERRABLE INITIALLY DEFERRED""")
    op.execute("""CREATE TABLE app_private.managed_faq_state (
        id INTEGER PRIMARY KEY CHECK (id = 1), generation BIGINT NOT NULL CHECK (generation >= 0)
    )""")
    op.execute("INSERT INTO app_private.managed_faq_state VALUES (1, 0)")
    op.execute("""CREATE INDEX ix_managed_faq_published ON app_private.managed_faq (id)
        WHERE published_revision IS NOT NULL""")
    for table, actions in (
        ("managed_faq", ("SELECT", "INSERT", "UPDATE")),
        ("managed_faq_revision", ("SELECT", "INSERT")),
        ("managed_faq_state", ("SELECT", "UPDATE")),
    ):
        op.execute(f"REVOKE ALL ON app_private.{table} FROM PUBLIC, vgu_buddy_runtime")
        op.execute(f"""DO $$ DECLARE r text; BEGIN
            FOREACH r IN ARRAY ARRAY['anon','authenticated','service_role'] LOOP
                IF EXISTS(SELECT 1 FROM pg_roles WHERE rolname=r) THEN
                    EXECUTE format('REVOKE ALL ON app_private.{table} FROM %I',r);
                END IF;
            END LOOP;
        END $$""")
        op.execute(f"ALTER TABLE app_private.{table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"GRANT {','.join(actions)} ON app_private.{table} TO vgu_buddy_runtime")
        for action in actions:
            predicate = "WITH CHECK (true)" if action == "INSERT" else "USING (true)"
            op.execute(f"""CREATE POLICY {table}_{action.lower()} ON app_private.{table}
                FOR {action} TO vgu_buddy_runtime {predicate}""")


def downgrade() -> None:
    op.execute("ALTER TABLE app_private.managed_faq DROP CONSTRAINT fk_managed_draft_revision")
    op.execute("ALTER TABLE app_private.managed_faq DROP CONSTRAINT fk_managed_published_revision")
    op.drop_table("managed_faq_revision", schema="app_private")
    op.drop_table("managed_faq", schema="app_private")
    op.drop_table("managed_faq_state", schema="app_private")
