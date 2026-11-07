"""Store the published User Side theme."""

from alembic import op

revision = "0026_site_theme"
down_revision = "0025_managed_faq"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""CREATE TABLE app_private.site_theme (
        singleton BOOLEAN PRIMARY KEY DEFAULT true CHECK (singleton),
        theme TEXT NOT NULL CHECK (theme IN ('default', 'halloween', 'christmas', 'summer'))
    )""")
    op.execute(
        "INSERT INTO app_private.site_theme (theme) VALUES ('default') ON CONFLICT DO NOTHING"
    )
    op.execute("REVOKE ALL ON app_private.site_theme FROM PUBLIC, vgu_buddy_runtime")
    op.execute("""DO $$ DECLARE r text; BEGIN
        FOREACH r IN ARRAY ARRAY['anon','authenticated','service_role'] LOOP
            IF EXISTS(SELECT FROM pg_roles WHERE rolname=r) THEN
                EXECUTE format('REVOKE ALL ON app_private.site_theme FROM %I',r);
            END IF;
        END LOOP;
    END $$""")
    op.execute("ALTER TABLE app_private.site_theme ENABLE ROW LEVEL SECURITY")
    op.execute("GRANT SELECT, INSERT, UPDATE ON app_private.site_theme TO vgu_buddy_runtime")
    op.execute("""CREATE POLICY site_theme_read ON app_private.site_theme
        FOR SELECT TO vgu_buddy_runtime USING (true)""")
    op.execute("""CREATE POLICY site_theme_seed ON app_private.site_theme
        FOR INSERT TO vgu_buddy_runtime WITH CHECK (singleton AND theme = 'default')""")
    op.execute("""CREATE POLICY site_theme_publish ON app_private.site_theme
        FOR UPDATE TO vgu_buddy_runtime USING (true) WITH CHECK (singleton)""")


def downgrade() -> None:
    op.drop_table("site_theme", schema="app_private")
