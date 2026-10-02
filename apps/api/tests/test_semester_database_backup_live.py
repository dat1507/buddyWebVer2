"""Opt-in SEM-002 backup/restore acceptance on two clean disposable PostgreSQL DBs.

Set SEM002_SOURCE_DATABASE_URL and SEM002_TARGET_DATABASE_URL to the loopback-only
``sem002_source`` and ``sem002_target`` databases owned by ``sem002_runner``. Both
databases are migrated, populated/rehearsed, and returned to Alembic base.
"""

from __future__ import annotations

import asyncio
import os
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from alembic.config import Config
from pydantic import SecretStr
from sqlalchemy import text
from sqlalchemy.engine import URL, make_url
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

from alembic import command
from app.core.config import (
    MIGRATION_URL_VARIABLE,
    BackupDatabaseSettings,
    get_migration_database_settings,
)
from app.models import SemesterBackupState
from app.services.database_backup_storage import (
    DatabaseBackupArtifactStore,
    DatabaseBackupObjectKind,
    DatabaseBackupObjectRef,
    DatabaseBackupStorageError,
    PrivateFileDatabaseBackupStore,
)
from app.services.semester_database_backup import (
    DatabaseBackupAlreadyAttachedError,
    DatabaseBackupError,
    PostgresBinaryCopyBackupAdapter,
    create_semester_database_backup,
    load_database_backup_from_storage,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
NOW = datetime(2026, 10, 2, 8, 0, tzinfo=UTC)


def _config() -> Config:
    return Config(toml_file=PROJECT_ROOT / "pyproject.toml")


def _validated_url(variable: str, database: str) -> URL:
    raw = os.getenv(variable)
    if not raw:
        pytest.skip(f"Set {variable} for disposable SEM-002 acceptance.")
    parsed = make_url(raw)
    if (
        parsed.host != "127.0.0.1"
        or parsed.database != database
        or parsed.username != "sem002_runner"
    ):
        pytest.fail(f"{variable} must target sem002_runner in loopback {database}.")
    return parsed


def _async_url(url: URL) -> str:
    return url.set(drivername="postgresql+asyncpg", query={"ssl": "disable"}).render_as_string(
        hide_password=False
    )


async def _seed_source(engine: AsyncEngine) -> dict[str, UUID]:
    ids = {
        "admin": uuid4(),
        "user_one": uuid4(),
        "user_two": uuid4(),
        "profile_one": uuid4(),
        "profile_two": uuid4(),
        "photo": uuid4(),
        "token": uuid4(),
        "session": uuid4(),
        "custom": uuid4(),
        "invitation": uuid4(),
        "match": uuid4(),
        "conversation": uuid4(),
        "message": uuid4(),
        "outbox": uuid4(),
        "operation": uuid4(),
        "backup": uuid4(),
        "failure_operation": uuid4(),
        "failure_backup": uuid4(),
    }
    async with engine.begin() as connection:
        semester_row = (
            await connection.execute(
                text("SELECT id, started_at FROM app_private.semesters WHERE status = 'CURRENT'")
            )
        ).one()
        semester_id = semester_row.id
        source_boundary_at = semester_row.started_at
        assert isinstance(semester_id, UUID)
        ids["semester"] = semester_id
        interest_id = await connection.scalar(
            text("SELECT id FROM app_private.interests WHERE code = 'photography'")
        )
        activity_id = await connection.scalar(
            text("SELECT id FROM app_private.activities ORDER BY code LIMIT 1")
        )
        assert isinstance(interest_id, UUID)
        assert isinstance(activity_id, UUID)
        ids["interest"] = interest_id
        ids["activity"] = activity_id
        await connection.execute(
            text(
                "INSERT INTO app_private.users "
                "(id, email, password_hash, role, email_verified, email_verified_at, "
                "semester_id, created_at) VALUES "
                "(:admin, 'sem002-admin@example.invalid', 'admin-hash', 'ADMIN', true, :now, "
                "NULL, :now), "
                "(:user_one, 'sem002-one@example.invalid', 'user-one-hash', 'USER', true, "
                ":now, :semester, :now), "
                "(:user_two, 'sem002-two@example.invalid', 'user-two-hash', 'USER', true, "
                ":now, :semester, :now)"
            ),
            {**ids, "now": NOW},
        )
        await connection.execute(
            text(
                "INSERT INTO app_private.student_profiles "
                "(id, user_id, full_name, display_name, student_type, nationality, major, "
                "study_year, bio, availability, preferences, matching_opt_in, "
                "onboarding_completed_at, created_at) VALUES "
                "(:profile_one, :user_one, 'Student One', 'One', 'VIETNAMESE', 'Vietnamese', "
                "'CS', 3, 'Backup one', '{}'::jsonb, '{}'::jsonb, true, :now, :now), "
                "(:profile_two, :user_two, 'Student Two', 'Two', 'INTERNATIONAL', 'German', "
                "'Business', 2, 'Backup two', '{}'::jsonb, '{}'::jsonb, true, :now, :now)"
            ),
            {**ids, "now": NOW},
        )
        await connection.execute(
            text(
                "INSERT INTO app_private.profile_photos "
                "(id, profile_id, bucket, object_key, mime_type, byte_size, width, height, "
                "is_avatar, processing_status, created_at) VALUES "
                "(:photo, :profile_one, 'profile-images', :object_key, 'image/jpeg', 128, 64, "
                "64, true, 'READY', :now)"
            ),
            {**ids, "object_key": f"{uuid4()}.jpg", "now": NOW},
        )
        await connection.execute(
            text(
                "INSERT INTO app_private.profile_interests (profile_id, interest_id) VALUES "
                "(:profile_one, :interest), (:profile_two, :interest)"
            ),
            ids,
        )
        await connection.execute(
            text(
                "INSERT INTO app_private.profile_languages "
                "(profile_id, language_code, proficiency) VALUES "
                "(:profile_one, 'en', 'fluent'), (:profile_two, 'en', 'native')"
            ),
            ids,
        )
        await connection.execute(
            text(
                "INSERT INTO app_private.profile_activities (profile_id, activity_id) VALUES "
                "(:profile_one, :activity), (:profile_two, :activity)"
            ),
            ids,
        )
        await connection.execute(
            text(
                "INSERT INTO app_private.profile_custom_preferences "
                "(id, profile_id, kind, display_label, normalized_key, proficiency, created_at) "
                "VALUES (:custom, :profile_one, 'LANGUAGE', 'Thai', 'thai', 'beginner', :now)"
            ),
            {**ids, "now": NOW},
        )
        await connection.execute(
            text(
                "INSERT INTO app_private.email_verification_tokens "
                "(id, user_id, token_digest, email_snapshot, expires_at, created_at) VALUES "
                "(:token, :user_one, :digest, 'sem002-one@example.invalid', :expires, :now)"
            ),
            {
                **ids,
                "digest": b"sem002-digest" * 3,
                "expires": NOW + timedelta(days=7),
                "now": NOW,
            },
        )
        await connection.execute(
            text(
                "INSERT INTO app_private.refresh_sessions "
                "(id, user_id, refresh_token_id, expires_at, created_at) VALUES "
                "(:session, :user_one, :refresh_id, :expires, :now)"
            ),
            {
                **ids,
                "refresh_id": uuid4(),
                "expires": NOW + timedelta(days=7),
                "now": NOW,
            },
        )
        await connection.execute(
            text(
                "INSERT INTO app_private.matching_invitations "
                "(id, sender_id, recipient_id, message, status, expires_at, responded_at, "
                "created_at) VALUES "
                "(:invitation, :user_one, :user_two, 'Let us be buddies', 'ACCEPTED', "
                ":expires, :responded, :now)"
            ),
            {
                **ids,
                "expires": NOW + timedelta(days=7),
                "responded": NOW + timedelta(hours=1),
                "now": NOW,
            },
        )
        await connection.execute(
            text(
                "INSERT INTO app_private.matches "
                "(id, participant_one_user_id, participant_two_user_id, "
                "participant_one_profile_id, participant_two_profile_id, status, "
                "accepted_invitation_id, semester_id, score, score_breakdown, activated_at, "
                "created_at) VALUES "
                "(:match, :user_one, :user_two, :profile_one, :profile_two, 'ACTIVE', "
                ":invitation, :semester, 87, CAST(:score_breakdown AS jsonb), :responded, :now)"
            ),
            {
                **ids,
                "score_breakdown": '{"interest":87}',
                "responded": NOW + timedelta(hours=1),
                "now": NOW,
            },
        )
        await connection.execute(
            text(
                "INSERT INTO app_private.buddy_conversations "
                "(id, match_id, semester_id, created_at) VALUES "
                "(:conversation, :match, :semester, :responded)"
            ),
            {**ids, "responded": NOW + timedelta(hours=1)},
        )
        await connection.execute(
            text(
                "INSERT INTO app_private.buddy_messages "
                "(id, conversation_id, sender_id, client_message_id, body, expires_at, "
                "created_at) VALUES "
                "(:message, :conversation, :user_one, :client_message, 'Restorable hello', "
                ":message_expires, :responded)"
            ),
            {
                **ids,
                "client_message": uuid4(),
                "responded": NOW + timedelta(hours=1),
                "message_expires": NOW + timedelta(hours=1, days=90),
            },
        )
        await connection.execute(
            text(
                "INSERT INTO app_private.transactional_outbox "
                "(id, event_type, aggregate_id, recipient_user_id, recipient_email, "
                "idempotency_key, payload, next_attempt_at, created_at) VALUES "
                "(:outbox, 'invitation.created', :invitation, :user_two, "
                "'sem002-two@example.invalid', :idempotency, CAST(:payload AS jsonb), "
                ":now, :now)"
            ),
            {
                **ids,
                "idempotency": f"sem002-{ids['outbox']}",
                "payload": '{"safe":true}',
                "now": NOW,
            },
        )
        await connection.execute(
            text(
                "INSERT INTO app_private.semester_operations "
                "(id, operation_type, state, semester_id, admin_actor_id, requested_at, "
                "started_at) VALUES "
                "(:operation, 'RESET', 'RUNNING', :semester, :admin, :now, :now), "
                "(:failure_operation, 'RESET', 'REQUESTED', :semester, :admin, :now, NULL)"
            ),
            {**ids, "now": NOW},
        )
        await connection.execute(
            text(
                "INSERT INTO app_private.semester_backups "
                "(id, source_semester_id, source_boundary_at, created_by_operation_id) VALUES "
                "(:backup, :semester, :boundary, :operation), "
                "(:failure_backup, :semester, :boundary, :failure_operation)"
            ),
            {**ids, "boundary": source_boundary_at},
        )
    return ids


async def _seed_target_references(engine: AsyncEngine, ids: dict[str, UUID]) -> None:
    async with engine.begin() as connection:
        target_semester = await connection.scalar(
            text("SELECT id FROM app_private.semesters WHERE status = 'CURRENT'")
        )
        # Disposable-fixture setup only: align the shared reference identity before
        # any USER exists. Production semester identities remain immutable.
        await connection.execute(
            text(
                "ALTER TABLE app_private.semesters DISABLE TRIGGER trg_semesters_immutable_boundary"
            )
        )
        await connection.execute(
            text("UPDATE app_private.semesters SET id = :source WHERE id = :target"),
            {"source": ids["semester"], "target": target_semester},
        )
        await connection.execute(
            text(
                "ALTER TABLE app_private.semesters ENABLE TRIGGER trg_semesters_immutable_boundary"
            )
        )
        await connection.execute(
            text(
                "INSERT INTO app_private.users "
                "(id, email, password_hash, role, email_verified, email_verified_at, created_at) "
                "VALUES (:admin, 'sem002-admin@example.invalid', 'admin-hash', 'ADMIN', true, "
                ":now, :now)"
            ),
            {**ids, "now": NOW},
        )
        target_interest = await connection.scalar(
            text("SELECT id FROM app_private.interests WHERE code = 'photography'")
        )
        target_activity = await connection.scalar(
            text("SELECT id FROM app_private.activities ORDER BY code LIMIT 1")
        )
        await connection.execute(
            text("UPDATE app_private.interests SET id = :source WHERE id = :target"),
            {"source": ids["interest"], "target": target_interest},
        )
        await connection.execute(
            text("UPDATE app_private.activities SET id = :source WHERE id = :target"),
            {"source": ids["activity"], "target": target_activity},
        )
        target_interest = await connection.scalar(
            text("SELECT id FROM app_private.interests WHERE code = 'photography'")
        )
        target_activity = await connection.scalar(
            text("SELECT id FROM app_private.activities ORDER BY code LIMIT 1")
        )
        assert target_interest == ids["interest"]
        assert target_activity == ids["activity"]


class _FailAfterArtifactStore(DatabaseBackupArtifactStore):
    def __init__(self, delegate: PrivateFileDatabaseBackupStore) -> None:
        self.delegate = delegate

    def location(self, reference: DatabaseBackupObjectRef) -> str:
        return self.delegate.location(reference)

    async def put_file(self, reference: DatabaseBackupObjectRef, source: Path) -> None:
        if reference.kind is DatabaseBackupObjectKind.MANIFEST:
            raise DatabaseBackupStorageError("injected private detail")
        await self.delegate.put_file(reference, source)

    async def get_file(self, reference: DatabaseBackupObjectRef, target: Path) -> None:
        await self.delegate.get_file(reference, target)

    async def delete(self, reference: DatabaseBackupObjectRef) -> None:
        await self.delegate.delete(reference)


async def _exercise(
    source_url: URL,
    target_url: URL,
    artifact_root: Path,
) -> None:
    source_engine = create_async_engine(_async_url(source_url), poolclass=NullPool)
    target_engine = create_async_engine(_async_url(target_url), poolclass=NullPool)
    source_factory = async_sessionmaker(
        source_engine, expire_on_commit=False, autoflush=False, class_=AsyncSession
    )
    try:
        ids = await _seed_source(source_engine)
        await _seed_target_references(target_engine, ids)
        source_settings = BackupDatabaseSettings(url=SecretStr(source_url.render_as_string(False)))
        target_settings = BackupDatabaseSettings(url=SecretStr(target_url.render_as_string(False)))
        source_adapter = PostgresBinaryCopyBackupAdapter(source_settings)
        store = PrivateFileDatabaseBackupStore(artifact_root / "successful")

        report = await create_semester_database_backup(
            source_factory,
            backup_id=ids["backup"],
            adapter=source_adapter,
            storage=store,
        )
        assert report.state is SemesterBackupState.CREATING
        assert report.table_count == 15
        assert report.row_count >= 19

        with pytest.raises(DatabaseBackupAlreadyAttachedError):
            await create_semester_database_backup(
                source_factory,
                backup_id=ids["backup"],
                adapter=source_adapter,
                storage=store,
            )

        async with source_engine.connect() as connection:
            metadata = (
                await connection.execute(
                    text(
                        "SELECT state, database_manifest_location, "
                        "database_manifest_checksum, database_row_counts, verified_at, "
                        "expires_at, failure_code FROM app_private.semester_backups "
                        "WHERE id = :id"
                    ),
                    {"id": ids["backup"]},
                )
            ).one()
            assert metadata.state == "CREATING"
            assert metadata.database_manifest_location.startswith("private-file://")
            assert len(metadata.database_manifest_checksum) == 64
            assert metadata.database_row_counts["users"] == 2
            assert metadata.database_row_counts["matches"] == 1
            assert metadata.verified_at is None
            assert metadata.expires_at is None
            assert metadata.failure_code is None

        download_root = artifact_root / "downloaded"
        download_root.mkdir(mode=0o700)
        manifest, artifact_path, manifest_content = await load_database_backup_from_storage(
            store,
            backup_id=ids["backup"],
            manifest_checksum=report.manifest_checksum,
            workspace=download_root,
        )
        assert b"source-password" not in manifest_content
        assert b"postgresql://" not in manifest_content
        assert manifest.row_counts["profile_custom_preferences"] == 1
        assert manifest.row_counts["buddy_messages"] == 1
        assert manifest.row_counts["transactional_outbox"] == 1

        target_adapter = PostgresBinaryCopyBackupAdapter(target_settings)
        await target_adapter.restore_for_rehearsal(
            manifest_content=manifest_content,
            artifact_path=artifact_path,
            expected_manifest_checksum=report.manifest_checksum,
        )
        async with target_engine.connect() as connection:
            assert (
                await connection.scalar(
                    text("SELECT count(*) FROM app_private.users WHERE role = 'USER'")
                )
                == 2
            )
            assert (
                await connection.scalar(
                    text("SELECT count(*) FROM app_private.users WHERE role = 'ADMIN'")
                )
                == 1
            )
            assert await connection.scalar(text("SELECT count(*) FROM app_private.interests")) == 13
            assert (
                await connection.scalar(
                    text("SELECT count(*) FROM app_private.profile_custom_preferences")
                )
                == 1
            )
            assert await connection.scalar(text("SELECT count(*) FROM app_private.matches")) == 1
            assert (
                await connection.scalar(
                    text("SELECT count(*) FROM app_private.buddy_conversations")
                )
                == 1
            )
            assert (
                await connection.scalar(text("SELECT body FROM app_private.buddy_messages"))
                == "Restorable hello"
            )
            assert (
                await connection.scalar(
                    text("SELECT count(*) FROM app_private.transactional_outbox")
                )
                == 1
            )

        failing_store_root = artifact_root / "failing"
        async with source_engine.begin() as connection:
            await connection.execute(
                text(
                    "UPDATE app_private.semester_operations SET state = 'FAILED', "
                    "completed_at = :completed, failure_code = 'TEST_NEXT_BACKUP' "
                    "WHERE id = :operation"
                ),
                {**ids, "completed": NOW + timedelta(hours=2)},
            )
            await connection.execute(
                text(
                    "UPDATE app_private.semester_operations SET state = 'RUNNING', "
                    "started_at = :started WHERE id = :failure_operation"
                ),
                {**ids, "started": NOW + timedelta(hours=2)},
            )
        failing_store = _FailAfterArtifactStore(PrivateFileDatabaseBackupStore(failing_store_root))
        with pytest.raises(DatabaseBackupError):
            await create_semester_database_backup(
                source_factory,
                backup_id=ids["failure_backup"],
                adapter=source_adapter,
                storage=failing_store,
            )
        async with source_engine.connect() as connection:
            failed = (
                await connection.execute(
                    text(
                        "SELECT state, failure_code, database_manifest_location "
                        "FROM app_private.semester_backups WHERE id = :id"
                    ),
                    {"id": ids["failure_backup"]},
                )
            ).one()
            assert failed == ("FAILED", "DATABASE_BACKUP_FAILED", None)
            assert (
                await connection.scalar(
                    text("SELECT count(*) FROM app_private.users WHERE role = 'USER'")
                )
                == 2
            )
        assert not any(failing_store_root.rglob("*.*"))
    finally:
        await source_engine.dispose()
        await target_engine.dispose()


def test_live_scoped_backup_restores_to_second_clean_postgresql(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    source_url = _validated_url("SEM002_SOURCE_DATABASE_URL", "sem002_source")
    target_url = _validated_url("SEM002_TARGET_DATABASE_URL", "sem002_target")
    config = _config()
    try:
        for url in (source_url, target_url):
            monkeypatch.setenv(MIGRATION_URL_VARIABLE, url.render_as_string(False))
            get_migration_database_settings.cache_clear()
            command.upgrade(config, "head")
        asyncio.run(_exercise(source_url, target_url, tmp_path / "private-artifacts"))
        for url in (source_url, target_url):
            monkeypatch.setenv(MIGRATION_URL_VARIABLE, url.render_as_string(False))
            get_migration_database_settings.cache_clear()
            command.check(config)
    finally:
        for url in (source_url, target_url):
            monkeypatch.setenv(MIGRATION_URL_VARIABLE, url.render_as_string(False))
            get_migration_database_settings.cache_clear()
            command.downgrade(config, "base")
        get_migration_database_settings.cache_clear()
