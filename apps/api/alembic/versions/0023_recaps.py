"""Independent recap publication and private upload derivatives. Local-only until release approval."""

from alembic import op

revision = "0023_recaps"
down_revision = "0022_public_event_visibility_default"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
CREATE TABLE app_private.recaps (
	related_event_id UUID,
	title_en TEXT,
	title_de TEXT,
	summary_en TEXT,
	summary_de TEXT,
	editorial_en TEXT,
	editorial_de TEXT,
	event_date DATE,
	status TEXT DEFAULT 'DRAFT' NOT NULL,
	version INTEGER DEFAULT 1 NOT NULL,
	thumbnail_id UUID,
	created_by UUID NOT NULL,
	updated_by UUID NOT NULL,
	id UUID DEFAULT gen_random_uuid() NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	deleted_at TIMESTAMP WITH TIME ZONE,
	CONSTRAINT pk_recaps PRIMARY KEY (id),
	CONSTRAINT ck_recaps_status CHECK (status IN ('DRAFT', 'PUBLISHED', 'ARCHIVED')),
	CONSTRAINT ck_recaps_version CHECK (version >= 1),
	CONSTRAINT fk_recaps_related_event_id_events FOREIGN KEY(related_event_id) REFERENCES app_private.events (id) ON DELETE RESTRICT,
	CONSTRAINT fk_recaps_created_by_users FOREIGN KEY(created_by) REFERENCES app_private.users (id) ON DELETE RESTRICT,
	CONSTRAINT fk_recaps_updated_by_users FOREIGN KEY(updated_by) REFERENCES app_private.users (id) ON DELETE RESTRICT
);
"""
    )
    op.execute(
        "CREATE INDEX ix_recaps_public_order ON app_private.recaps (status, event_date, created_at, id);"
    )
    op.execute(
        """
CREATE TABLE app_private.recap_photos (
	recap_id UUID NOT NULL,
	upload_id UUID NOT NULL,
	fingerprint TEXT NOT NULL,
	alt_en TEXT DEFAULT '' NOT NULL,
	alt_de TEXT DEFAULT '' NOT NULL,
	caption_en TEXT,
	caption_de TEXT,
	sort_order INTEGER NOT NULL,
	id UUID DEFAULT gen_random_uuid() NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	deleted_at TIMESTAMP WITH TIME ZONE,
	CONSTRAINT pk_recap_photos PRIMARY KEY (id),
	CONSTRAINT uq_recap_photo_owner UNIQUE (id, recap_id),
	CONSTRAINT uq_recap_photo_retry UNIQUE (recap_id, upload_id),
	CONSTRAINT ck_recap_photo_order CHECK (sort_order BETWEEN 0 AND 11),
	CONSTRAINT ck_recap_photo_alt CHECK (char_length(alt_en) <= 200 AND char_length(alt_de) <= 200),
	CONSTRAINT fk_recap_photos_recap_id_recaps FOREIGN KEY(recap_id) REFERENCES app_private.recaps (id) ON DELETE CASCADE
);
"""
    )
    op.execute(
        "CREATE INDEX ix_recap_photos_recap_order ON app_private.recap_photos (recap_id, sort_order);"
    )
    op.execute(
        """
CREATE TABLE app_private.recap_images (
	photo_id UUID NOT NULL,
	bucket TEXT DEFAULT 'event-media' NOT NULL,
	object_key TEXT NOT NULL,
	variant TEXT NOT NULL,
	byte_size INTEGER NOT NULL,
	width INTEGER NOT NULL,
	height INTEGER NOT NULL,
	id UUID DEFAULT gen_random_uuid() NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	deleted_at TIMESTAMP WITH TIME ZONE,
	CONSTRAINT pk_recap_images PRIMARY KEY (id),
	CONSTRAINT uq_recap_image_variant UNIQUE (photo_id, variant),
	CONSTRAINT ck_recap_image_variant CHECK (variant IN ('thumbnail', 'display')),
	CONSTRAINT ck_recap_image_bucket CHECK (bucket = 'event-media'),
	CONSTRAINT ck_recap_image_bytes CHECK (byte_size BETWEEN 1 AND 5242880),
	CONSTRAINT ck_recap_image_size CHECK (width BETWEEN 1 AND 1600 AND height BETWEEN 1 AND 1600),
	CONSTRAINT fk_recap_images_photo_id_recap_photos FOREIGN KEY(photo_id) REFERENCES app_private.recap_photos (id) ON DELETE CASCADE,
	CONSTRAINT uq_recap_images_object_key UNIQUE (object_key)
);
"""
    )
    op.execute(
        "ALTER TABLE app_private.recaps ADD CONSTRAINT fk_recaps_thumbnail_owner FOREIGN KEY(thumbnail_id, id) REFERENCES app_private.recap_photos (id, recap_id) ON DELETE RESTRICT;"
    )
    for table in ("recaps", "recap_photos", "recap_images"):
        op.execute(f"REVOKE ALL ON TABLE app_private.{table} FROM PUBLIC")
        op.execute(f"ALTER TABLE app_private.{table} ENABLE ROW LEVEL SECURITY")
        op.execute(
            f"GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE app_private.{table} TO vgu_buddy_runtime"
        )
        op.execute(
            f"CREATE POLICY {table}_backend_access ON app_private.{table} FOR ALL TO vgu_buddy_runtime USING (true) WITH CHECK (true)"
        )
        op.execute(f"""DO $$ DECLARE api_role text; BEGIN
            FOREACH api_role IN ARRAY ARRAY['anon','authenticated','service_role'] LOOP
                IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = api_role) THEN
                    EXECUTE format('REVOKE ALL ON TABLE app_private.%I FROM %I', '{table}', api_role);
                END IF;
            END LOOP;
        END $$""")


def downgrade() -> None:
    op.execute("ALTER TABLE app_private.recaps DROP CONSTRAINT fk_recaps_thumbnail_owner")
    for table in ("recap_images", "recap_photos", "recaps"):
        op.drop_table(table, schema="app_private")
