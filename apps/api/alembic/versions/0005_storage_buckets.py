"""Create server-only object policies for managed image buckets.

Revision ID: 0005_storage_buckets
Revises: 0004_audit_logs
Create Date: 2026-09-19
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0005_storage_buckets"
down_revision: str | Sequence[str] | None = "0004_audit_logs"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_BUCKET_IDS = "'profile-images', 'event-media', 'event-slider-images'"


def upgrade() -> None:
    """Deny browser roles access to managed buckets when Supabase Storage is present."""
    op.execute(
        f"""
        DO $vgu_buddy_storage$
        BEGIN
            IF to_regclass('storage.objects') IS NULL THEN
                RAISE NOTICE 'Supabase Storage schema is unavailable; policies skipped';
                RETURN;
            END IF;

            EXECUTE 'DROP POLICY IF EXISTS vgu_buddy_clients_no_image_select '
                    'ON storage.objects';
            EXECUTE 'DROP POLICY IF EXISTS vgu_buddy_clients_no_image_insert '
                    'ON storage.objects';
            EXECUTE 'DROP POLICY IF EXISTS vgu_buddy_clients_no_image_update '
                    'ON storage.objects';
            EXECUTE 'DROP POLICY IF EXISTS vgu_buddy_clients_no_image_delete '
                    'ON storage.objects';

            EXECUTE $policy$
                CREATE POLICY vgu_buddy_clients_no_image_select
                ON storage.objects
                AS RESTRICTIVE
                FOR SELECT
                TO anon, authenticated
                USING (bucket_id NOT IN ({_BUCKET_IDS}))
            $policy$;
            EXECUTE $policy$
                CREATE POLICY vgu_buddy_clients_no_image_insert
                ON storage.objects
                AS RESTRICTIVE
                FOR INSERT
                TO anon, authenticated
                WITH CHECK (bucket_id NOT IN ({_BUCKET_IDS}))
            $policy$;
            EXECUTE $policy$
                CREATE POLICY vgu_buddy_clients_no_image_update
                ON storage.objects
                AS RESTRICTIVE
                FOR UPDATE
                TO anon, authenticated
                USING (bucket_id NOT IN ({_BUCKET_IDS}))
                WITH CHECK (bucket_id NOT IN ({_BUCKET_IDS}))
            $policy$;
            EXECUTE $policy$
                CREATE POLICY vgu_buddy_clients_no_image_delete
                ON storage.objects
                AS RESTRICTIVE
                FOR DELETE
                TO anon, authenticated
                USING (bucket_id NOT IN ({_BUCKET_IDS}))
            $policy$;
        END
        $vgu_buddy_storage$;
        """
    )


def downgrade() -> None:
    """Remove managed-bucket policies without mutating Storage API resources."""
    op.execute(
        """
        DO $vgu_buddy_storage$
        BEGIN
            IF to_regclass('storage.objects') IS NULL THEN
                RETURN;
            END IF;

            EXECUTE 'DROP POLICY IF EXISTS vgu_buddy_clients_no_image_delete '
                    'ON storage.objects';
            EXECUTE 'DROP POLICY IF EXISTS vgu_buddy_clients_no_image_update '
                    'ON storage.objects';
            EXECUTE 'DROP POLICY IF EXISTS vgu_buddy_clients_no_image_insert '
                    'ON storage.objects';
            EXECUTE 'DROP POLICY IF EXISTS vgu_buddy_clients_no_image_select '
                    'ON storage.objects';
        END
        $vgu_buddy_storage$;
        """
    )
