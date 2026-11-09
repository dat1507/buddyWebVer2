"""Allow the Vietnamese Tet site theme without changing the published preset."""

from alembic import op

revision = "0027_site_theme_tet"
down_revision = "0026_site_theme"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""ALTER TABLE app_private.site_theme
        DROP CONSTRAINT site_theme_theme_check,
        ADD CONSTRAINT site_theme_theme_check
            CHECK (theme IN ('default', 'halloween', 'christmas', 'summer', 'tet'))""")


def downgrade() -> None:
    raise NotImplementedError("This migration is forward-only.")
