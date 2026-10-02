"""Opt-in PostgreSQL 17 and private-storage acceptance for SEM-005.

Set ``SEM005_TEST_DATABASE_URL`` to the isolated loopback ``sem005_acceptance``
database owned by ``sem005_runner``. The test never targets a shared environment.
"""

from __future__ import annotations

import asyncio
import os
from datetime import UTC, datetime, timedelta
from io import BytesIO
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from alembic.config import Config
from PIL import Image
from pydantic import SecretStr
from sqlalchemy import text
from sqlalchemy.engine import URL, make_url
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from alembic import command
from app.core.config import (
    MIGRATION_URL_VARIABLE,
    BackupDatabaseSettings,
    get_migration_database_settings,
)
from app.models import SemesterBackupState
from app.services.database_backup_storage import (
    DatabaseBackupObjectKind,
    DatabaseBackupObjectRef,
    PrivateFileDatabaseBackupStore,
)
from app.services.image_storage import (
    ImageBucket,
    ImageStorageService,
    ListedStorageObject,
    StorageObjectRef,
    StorageOperationError,
    prepare_image,
)
from app.services.passwords import hash_password, verify_password
from app.services.semester_avatar_backup import AvatarBackupAdapter, create_semester_avatar_backup
from app.services.semester_backup_verification import verify_semester_backup
from app.services.semester_database_backup import (
    PostgresBinaryCopyBackupAdapter,
    create_semester_database_backup,
)
from app.services.semester_reset import (
    SemesterResetBusyError,
    SemesterResetSnapshotError,
    SemesterResetStateError,
    SemesterResetStorageError,
    execute_semester_reset,
    semester_reset_confirmation_phrase,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
NOW = datetime(2026, 10, 2, 8, 0, tzinfo=UTC)
ADMIN_PASSWORD = "Correct horse battery staple 2026!"


def _config() -> Config:
    return Config(toml_file=PROJECT_ROOT / "pyproject.toml")


def _validated_url() -> URL:
    raw = os.getenv("SEM005_TEST_DATABASE_URL")
    if not raw:
        pytest.skip("Set SEM005_TEST_DATABASE_URL for disposable SEM-005 acceptance.")
    parsed = make_url(raw)
    if (
        parsed.host != "127.0.0.1"
        or parsed.database != "sem005_acceptance"
        or parsed.username != "sem005_runner"
    ):
        pytest.fail(
            "SEM-005 requires sem005_runner in the isolated loopback sem005_acceptance database."
        )
    return parsed


def _async_url(url: URL) -> str:
    return url.set(drivername="postgresql+asyncpg", query={"ssl": "disable"}).render_as_string(
        hide_password=False
    )


def _avatar_bytes() -> bytes:
    output = BytesIO()
    Image.new("RGB", (32, 32), (20, 40, 60)).save(output, format="JPEG")
    return prepare_image(
        original_name="avatar.jpg",
        declared_content_type="image/jpeg",
        content=output.getvalue(),
    ).content


class _ControlledAvatarTransport:
    def __init__(self) -> None:
        self.objects: dict[StorageObjectRef, bytes] = {}
        self.fail_delete_once = False
        self.pause_delete = False
        self.delete_started = asyncio.Event()
        self.release_delete = asyncio.Event()

    async def upload(
        self,
        reference: StorageObjectRef,
        content: bytes,
        content_type: str,
    ) -> None:
        del content_type
        if reference in self.objects:
            raise StorageOperationError("Object exists.", status_code=409)
        self.objects[reference] = content

    async def delete(self, reference: StorageObjectRef) -> None:
        if self.fail_delete_once:
            self.fail_delete_once = False
            raise StorageOperationError("Injected private provider failure.", status_code=503)
        if self.pause_delete:
            self.delete_started.set()
            await self.release_delete.wait()
            self.pause_delete = False
        if reference not in self.objects:
            raise StorageOperationError("Object is absent.", status_code=404)
        del self.objects[reference]

    async def download(self, reference: StorageObjectRef) -> bytes:
        try:
            return self.objects[reference]
        except KeyError:
            raise StorageOperationError("Object is absent.", status_code=404) from None

    async def list_objects(
        self,
        bucket: ImageBucket,
        *,
        limit: int,
        offset: int,
    ) -> tuple[ListedStorageObject, ...]:
        keys = sorted(ref.object_key for ref in self.objects if ref.bucket is bucket)
        return tuple(ListedStorageObject(key, NOW) for key in keys[offset : offset + limit])

    async def create_signed_url(
        self,
        reference: StorageObjectRef,
        expires_in: int,
    ) -> str:
        del reference, expires_in
        raise AssertionError("Reset must never create a signed URL.")

    def public_url(self, reference: StorageObjectRef) -> str:
        del reference
        raise AssertionError("Reset must never create a public URL.")


async def _seed(engine: AsyncEngine, avatar: bytes) -> dict[str, UUID]:
    ids = {
        name: uuid4()
        for name in (
            "admin",
            "user_one",
            "user_two",
            "profile_one",
            "profile_two",
            "photo",
            "custom",
            "token",
            "refresh",
            "event",
            "registration",
            "invitation",
            "match",
            "conversation",
            "message",
            "outbox",
            "operation",
            "backup",
        )
    }
    async with engine.begin() as connection:
        semester = (
            await connection.execute(
                text("SELECT id, started_at FROM app_private.semesters WHERE status = 'CURRENT'")
            )
        ).one()
        ids["semester"] = semester.id
        ids["interest"] = await connection.scalar(
            text("SELECT id FROM app_private.interests ORDER BY code LIMIT 1")
        )
        ids["activity"] = await connection.scalar(
            text("SELECT id FROM app_private.activities ORDER BY code LIMIT 1")
        )
        await connection.execute(
            text(
                "INSERT INTO app_private.users "
                "(id, email, password_hash, role, email_verified, email_verified_at, "
                "semester_id, created_at) VALUES "
                "(:admin, 'sem005-admin@example.invalid', :admin_hash, 'ADMIN', true, :now, "
                "NULL, :now), "
                "(:user_one, 'sem005-vietnamese@example.invalid', 'student-hash', 'USER', true, "
                ":now, :semester, :now), "
                "(:user_two, 'sem005-international@example.invalid', 'student-hash', 'USER', "
                "true, :now, :semester, :now)"
            ),
            {**ids, "admin_hash": hash_password(ADMIN_PASSWORD), "now": NOW},
        )
        await connection.execute(
            text(
                "INSERT INTO app_private.student_profiles "
                "(id, user_id, full_name, display_name, student_type, bio, matching_opt_in, "
                "onboarding_completed_at, created_at) VALUES "
                "(:profile_one, :user_one, 'Vietnamese Student', 'Viet', 'VIETNAMESE', "
                "'Original profile', true, :now, :now), "
                "(:profile_two, :user_two, 'International Student', 'Intl', 'INTERNATIONAL', "
                "'Original profile', true, :now, :now)"
            ),
            {**ids, "now": NOW},
        )
        await connection.execute(
            text(
                "INSERT INTO app_private.profile_photos "
                "(id, profile_id, bucket, object_key, mime_type, byte_size, width, height, "
                "is_avatar, processing_status, created_at) VALUES "
                "(:photo, :profile_one, 'profile-images', :object_key, 'image/jpeg', "
                ":byte_size, 32, 32, true, 'READY', :now)"
            ),
            {
                **ids,
                "object_key": f"{ids['photo']}.jpg",
                "byte_size": len(avatar),
                "now": NOW,
            },
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
                "(:token, :user_one, :digest, 'sem005-vietnamese@example.invalid', :expires, :now)"
            ),
            {
                **ids,
                "digest": b"sem005-test-digest" * 2,
                "expires": NOW + timedelta(days=7),
                "now": NOW,
            },
        )
        await connection.execute(
            text(
                "INSERT INTO app_private.refresh_sessions "
                "(id, user_id, refresh_token_id, expires_at, created_at) VALUES "
                "(:refresh, :user_one, :refresh_id, :expires, :now)"
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
                "INSERT INTO app_private.events "
                "(id, title_en, title_de, created_by, updated_by, created_at) VALUES "
                "(:event, 'Shared Event', 'Gemeinsames Event', :admin, :admin, :now)"
            ),
            {**ids, "now": NOW},
        )
        await connection.execute(
            text(
                "INSERT INTO app_private.event_registrations "
                "(id, event_id, user_id, registered_at, status, created_at) VALUES "
                "(:registration, :event, :user_one, :now, 'registered', :now)"
            ),
            {**ids, "now": NOW},
        )
        await connection.execute(
            text(
                "INSERT INTO app_private.matching_invitations "
                "(id, sender_id, recipient_id, message, status, expires_at, responded_at, "
                "created_at) VALUES "
                "(:invitation, :user_one, :user_two, 'Buddy invitation', 'ACCEPTED', "
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
                ":invitation, :semester, 90, CAST(:score_breakdown AS jsonb), :responded, :now)"
            ),
            {
                **ids,
                "score_breakdown": '{"score":90}',
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
                "(:message, :conversation, :user_one, :client_message, 'Private message', "
                ":message_expires, :responded)"
            ),
            {
                **ids,
                "responded": NOW + timedelta(hours=1),
                "client_message": uuid4(),
                "message_expires": NOW + timedelta(days=90, hours=1),
            },
        )
        await connection.execute(
            text(
                "INSERT INTO app_private.transactional_outbox "
                "(id, event_type, aggregate_id, recipient_user_id, recipient_email, "
                "idempotency_key, payload, next_attempt_at, created_at) VALUES "
                "(:outbox, 'invitation.created', :invitation, :user_two, "
                "'sem005-international@example.invalid', :key, CAST(:payload AS jsonb), "
                ":now, :now)"
            ),
            {
                **ids,
                "key": f"sem005-{ids['outbox']}",
                "payload": '{"safe":true}',
                "now": NOW,
            },
        )
        await connection.execute(
            text(
                "INSERT INTO app_private.semester_operations "
                "(id, operation_type, state, semester_id, admin_actor_id, requested_at, "
                "started_at) VALUES "
                "(:operation, 'RESET', 'RUNNING', :semester, :admin, :now, :now)"
            ),
            {**ids, "now": NOW},
        )
        await connection.execute(
            text(
                "INSERT INTO app_private.semester_backups "
                "(id, source_semester_id, source_boundary_at, created_by_operation_id) VALUES "
                "(:backup, :semester, :boundary, :operation)"
            ),
            {
                **ids,
                "boundary": semester.started_at,
            },
        )
    return ids


async def _counts(engine: AsyncEngine, semester_id: UUID) -> dict[str, int]:
    table_names = (
        "users",
        "student_profiles",
        "profile_custom_preferences",
        "matching_invitations",
        "matches",
        "buddy_conversations",
        "buddy_messages",
    )
    counts: dict[str, int] = {}
    async with engine.connect() as connection:
        for table_name in table_names:
            if table_name == "users":
                query = "SELECT count(*) FROM app_private.users WHERE semester_id = :semester"
            elif table_name == "matches":
                query = "SELECT count(*) FROM app_private.matches WHERE semester_id = :semester"
            elif table_name == "buddy_conversations":
                query = (
                    "SELECT count(*) FROM app_private.buddy_conversations "
                    "WHERE semester_id = :semester"
                )
            elif table_name == "buddy_messages":
                query = (
                    "SELECT count(*) FROM app_private.buddy_messages WHERE conversation_id IN "
                    "(SELECT id FROM app_private.buddy_conversations "
                    "WHERE semester_id = :semester)"
                )
            elif table_name == "matching_invitations":
                query = (
                    "SELECT count(*) FROM app_private.matching_invitations WHERE sender_id IN "
                    "(SELECT id FROM app_private.users WHERE semester_id = :semester) "
                    "OR recipient_id IN "
                    "(SELECT id FROM app_private.users WHERE semester_id = :semester)"
                )
            else:
                query = (
                    f"SELECT count(*) FROM app_private.{table_name} WHERE profile_id IN "
                    "(SELECT profile.id FROM app_private.student_profiles AS profile "
                    "JOIN app_private.users AS owner ON owner.id = profile.user_id "
                    "WHERE owner.semester_id = :semester)"
                    if table_name != "student_profiles"
                    else "SELECT count(*) FROM app_private.student_profiles WHERE user_id IN "
                    "(SELECT id FROM app_private.users WHERE semester_id = :semester)"
                )
            counts[table_name] = int(
                await connection.scalar(text(query), {"semester": semester_id}) or 0
            )
    return counts


async def _acceptance(engine: AsyncEngine, backup_root: Path, parsed: URL) -> None:
    avatar = _avatar_bytes()
    ids = await _seed(engine, avatar)
    factory = async_sessionmaker(engine, expire_on_commit=False, autoflush=False)
    backup_settings = BackupDatabaseSettings(
        url=SecretStr(parsed.render_as_string(hide_password=False))
    )
    adapter = PostgresBinaryCopyBackupAdapter(backup_settings)
    backup_store = PrivateFileDatabaseBackupStore(backup_root)
    avatar_transport = _ControlledAvatarTransport()
    avatar_storage = ImageStorageService(avatar_transport)
    source_ref = StorageObjectRef(
        ImageBucket.PROFILE_IMAGES,
        f"{ids['photo']}.jpg",
    )
    unrelated_ref = StorageObjectRef(ImageBucket.PROFILE_IMAGES, f"{uuid4()}.jpg")
    avatar_transport.objects[source_ref] = avatar
    avatar_transport.objects[unrelated_ref] = b"unrelated"

    unverified_counts = await _counts(engine, ids["semester"])
    with pytest.raises(SemesterResetStateError):
        await execute_semester_reset(
            factory,
            operation_id=ids["operation"],
            backup_id=ids["backup"],
            admin_id=ids["admin"],
            current_password=ADMIN_PASSWORD,
            confirmation_phrase=semester_reset_confirmation_phrase(ids["semester"]),
            snapshot_adapter=adapter,
            backup_storage=backup_store,
            avatar_storage=avatar_storage,
        )
    assert await _counts(engine, ids["semester"]) == unverified_counts
    assert source_ref in avatar_transport.objects

    await create_semester_database_backup(
        factory,
        backup_id=ids["backup"],
        adapter=adapter,
        storage=backup_store,
    )
    await create_semester_avatar_backup(
        factory,
        backup_id=ids["backup"],
        adapter=AvatarBackupAdapter(avatar_storage),
        storage=backup_store,
    )
    preverified = await verify_semester_backup(
        factory,
        backup_id=ids["backup"],
        storage=backup_store,
    )
    assert preverified.persisted_state is SemesterBackupState.CREATING
    assert preverified.newly_verified is True
    baseline = await _counts(engine, ids["semester"])

    with pytest.raises(SemesterResetStateError):
        await execute_semester_reset(
            factory,
            operation_id=ids["operation"],
            backup_id=uuid4(),
            admin_id=ids["admin"],
            current_password=ADMIN_PASSWORD,
            confirmation_phrase=semester_reset_confirmation_phrase(ids["semester"]),
            snapshot_adapter=adapter,
            backup_storage=backup_store,
            avatar_storage=avatar_storage,
        )
    assert await _counts(engine, ids["semester"]) == baseline
    assert source_ref in avatar_transport.objects

    async with engine.begin() as connection:
        await connection.execute(
            text(
                "UPDATE app_private.student_profiles SET bio = 'Changed after backup' WHERE id = :id"
            ),
            {"id": ids["profile_one"]},
        )
    with pytest.raises(SemesterResetSnapshotError):
        await execute_semester_reset(
            factory,
            operation_id=ids["operation"],
            backup_id=ids["backup"],
            admin_id=ids["admin"],
            current_password=ADMIN_PASSWORD,
            confirmation_phrase=semester_reset_confirmation_phrase(ids["semester"]),
            snapshot_adapter=adapter,
            backup_storage=backup_store,
            avatar_storage=avatar_storage,
        )
    assert source_ref in avatar_transport.objects
    async with engine.begin() as connection:
        await connection.execute(
            text("UPDATE app_private.student_profiles SET bio = 'Original profile' WHERE id = :id"),
            {"id": ids["profile_one"]},
        )

    avatar_transport.fail_delete_once = True
    with pytest.raises(SemesterResetStorageError):
        await execute_semester_reset(
            factory,
            operation_id=ids["operation"],
            backup_id=ids["backup"],
            admin_id=ids["admin"],
            current_password=ADMIN_PASSWORD,
            confirmation_phrase=semester_reset_confirmation_phrase(ids["semester"]),
            snapshot_adapter=adapter,
            backup_storage=backup_store,
            avatar_storage=avatar_storage,
        )
    assert await _counts(engine, ids["semester"]) == baseline
    async with engine.connect() as connection:
        assert (
            await connection.scalar(
                text("SELECT state FROM app_private.semester_operations WHERE id = :id"),
                {"id": ids["operation"]},
            )
            == "RUNNING"
        )

    avatar_transport.pause_delete = True
    first = asyncio.create_task(
        execute_semester_reset(
            factory,
            operation_id=ids["operation"],
            backup_id=ids["backup"],
            admin_id=ids["admin"],
            current_password=ADMIN_PASSWORD,
            confirmation_phrase=semester_reset_confirmation_phrase(ids["semester"]),
            snapshot_adapter=adapter,
            backup_storage=backup_store,
            avatar_storage=avatar_storage,
        )
    )
    await asyncio.wait_for(avatar_transport.delete_started.wait(), timeout=10)
    with pytest.raises(SemesterResetBusyError):
        await execute_semester_reset(
            factory,
            operation_id=ids["operation"],
            backup_id=ids["backup"],
            admin_id=ids["admin"],
            current_password=ADMIN_PASSWORD,
            confirmation_phrase=semester_reset_confirmation_phrase(ids["semester"]),
            snapshot_adapter=adapter,
            backup_storage=backup_store,
            avatar_storage=avatar_storage,
        )
    avatar_transport.release_delete.set()
    report = await first
    assert report.backup_state is SemesterBackupState.READY
    assert report.idempotent_replay is False
    assert report.deleted_counts["users"] == 2
    assert report.deleted_counts["buddy_messages"] == 1
    assert report.avatar_objects_processed == 1

    replay = await execute_semester_reset(
        factory,
        operation_id=ids["operation"],
        backup_id=ids["backup"],
        admin_id=ids["admin"],
        current_password=ADMIN_PASSWORD,
        confirmation_phrase=semester_reset_confirmation_phrase(ids["semester"]),
        snapshot_adapter=adapter,
        backup_storage=backup_store,
        avatar_storage=avatar_storage,
    )
    assert replay.idempotent_replay is True
    assert replay.new_semester_id == report.new_semester_id
    assert await _counts(engine, ids["semester"]) == {key: 0 for key in baseline}
    assert source_ref not in avatar_transport.objects
    assert avatar_transport.objects[unrelated_ref] == b"unrelated"

    async with engine.connect() as connection:
        admin = (
            await connection.execute(
                text("SELECT role, password_hash FROM app_private.users WHERE id = :id"),
                {"id": ids["admin"]},
            )
        ).one()
        assert admin.role == "ADMIN"
        assert verify_password(ADMIN_PASSWORD, admin.password_hash)
        assert await connection.scalar(text("SELECT count(*) FROM app_private.interests")) > 0
        assert await connection.scalar(text("SELECT count(*) FROM app_private.languages")) > 0
        assert await connection.scalar(text("SELECT count(*) FROM app_private.activities")) > 0
        assert (
            await connection.scalar(
                text("SELECT count(*) FROM app_private.events WHERE id = :id"),
                {"id": ids["event"]},
            )
            == 1
        )
        persisted = (
            await connection.execute(
                text(
                    "SELECT operation.state AS operation_state, operation.completed_at, "
                    "backup.state AS backup_state, backup.expires_at, semester.status, "
                    "semester.reset_operation_id "
                    "FROM app_private.semester_operations AS operation "
                    "JOIN app_private.semester_backups AS backup ON backup.id = operation.backup_id "
                    "JOIN app_private.semesters AS semester ON semester.id = operation.semester_id "
                    "WHERE operation.id = :id"
                ),
                {"id": ids["operation"]},
            )
        ).one()
        assert persisted.operation_state == "SUCCEEDED"
        assert persisted.backup_state == "READY"
        assert persisted.status == "CLOSED"
        assert persisted.reset_operation_id == ids["operation"]
        assert persisted.expires_at - persisted.completed_at == timedelta(days=30)
        assert (
            await connection.scalar(
                text("SELECT count(*) FROM app_private.semesters WHERE status = 'CURRENT'")
            )
            == 1
        )
        assert (
            await connection.scalar(
                text("SELECT count(*) FROM app_private.audit_logs WHERE resource_id = :id"),
                {"id": ids["operation"]},
            )
            == 1
        )

    probe = backup_root / "probe-manifest.json"
    await backup_store.get_file(
        DatabaseBackupObjectRef(ids["backup"], DatabaseBackupObjectKind.MANIFEST),
        probe,
    )
    assert probe.stat().st_size > 0


def test_live_semester_reset_is_guarded_atomic_and_retry_safe(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    parsed = _validated_url()
    monkeypatch.setenv(MIGRATION_URL_VARIABLE, parsed.render_as_string(hide_password=False))
    get_migration_database_settings.cache_clear()
    config = _config()
    engine = create_async_engine(_async_url(parsed), poolclass=NullPool)
    try:
        command.upgrade(config, "head")
        command.downgrade(config, "0018_backup_verification")
        command.upgrade(config, "head")
        command.check(config)
        asyncio.run(_acceptance(engine, tmp_path / "private-backups", parsed))
        command.downgrade(config, "0018_backup_verification")
        command.upgrade(config, "head")
    finally:
        asyncio.run(engine.dispose())
        get_migration_database_settings.cache_clear()
