"""Opt-in local-only real PostgreSQL/API acceptance; no Production URL accepted.

RECAP_TEST_DATABASE_URL must name buddy_recap_local on buddy-recap-db or loopback.
The test owns disposable databases, migrates fresh and upgrades existing revisions.
"""

from __future__ import annotations

import asyncio
import os
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from io import BytesIO
from pathlib import Path
from uuid import uuid4

import pytest
from alembic.config import Config
from httpx2 import ASGITransport, AsyncClient, Response
from PIL import Image
from pydantic import SecretBytes
from sqlalchemy import select, text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from alembic import command
from app.api.dependencies import get_image_storage_service
from app.core.config import (
    AuthTokenSettings,
    CsrfSettings,
    get_auth_token_settings,
    get_csrf_settings,
)
from app.core.database import get_database_session
from app.main import app
from app.models import Event, EventStatus, EventVisibility, User, UserRole
from app.models.recap import RecapImage
from app.services.csrf import CSRF_HEADER_NAME, create_session_csrf_token, csrf_cookie_name
from app.services.image_storage import (
    ImageStorageService,
    StorageObjectRef,
    StorageOperationError,
    discover_storage_references,
)
from app.services.tokens import DEVELOPMENT_ACCESS_COOKIE_NAME, create_token_pair


class MemoryTransport:
    """Deterministic fault injection only; real provider transport is separately regression-tested."""

    def __init__(self) -> None:
        self.objects: dict[str, bytes] = {}
        self.fail_delete = False
        self.fail_upload = False

    async def upload(self, reference: StorageObjectRef, content: bytes, content_type: str) -> None:
        if self.fail_upload:
            raise StorageOperationError("Local injected outage")
        self.objects[reference.object_key] = content

    async def delete(self, reference: StorageObjectRef) -> None:
        if self.fail_delete:
            raise StorageOperationError("Local injected outage")
        self.objects.pop(reference.object_key, None)

    async def create_signed_url(self, reference: StorageObjectRef, expires_in: int) -> str:
        return "https://local-storage.invalid/authorized-image"


def local_url() -> str:
    value = os.getenv("RECAP_TEST_DATABASE_URL")
    if not value:
        pytest.skip("RECAP_TEST_DATABASE_URL not configured")
    url = make_url(value)
    if (
        url.host not in {"buddy-recap-db", "localhost", "127.0.0.1"}
        or url.database != "buddy_recap_local"
    ):
        pytest.fail("Refusing non-disposable database")
    return value


def migrate(url: str, revision: str) -> None:
    config = Config(toml_file=Path(__file__).resolve().parents[1] / "pyproject.toml")
    config.set_main_option("sqlalchemy.url", url.replace("%", "%%"))
    command.upgrade(config, revision)


def test_fresh_migrations_and_real_recap_lifecycle() -> None:
    url = local_url()
    # First install crosses the previously broken 36-character revision without fixture widening.
    migrate(url, "head")
    asyncio.run(acceptance(url))


def test_upgrade_from_existing_32_character_version_table() -> None:
    url = local_url()
    database_name = "buddy_recap_upgrade_" + uuid4().hex[:8]
    upgraded_url = make_url(url).set(database=database_name).render_as_string(hide_password=False)

    async def create_disposable() -> None:
        engine = create_async_engine(url, isolation_level="AUTOCOMMIT")
        async with engine.connect() as connection:
            await connection.execute(text("CREATE DATABASE " + database_name))
            await connection.execute(
                text("""DO $$ BEGIN
                IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname='anon') THEN CREATE ROLE anon NOLOGIN; END IF;
                IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname='authenticated') THEN CREATE ROLE authenticated NOLOGIN; END IF;
                IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname='service_role') THEN CREATE ROLE service_role NOLOGIN; END IF;
            END $$""")
            )
        await engine.dispose()

    asyncio.run(create_disposable())
    migrate(upgraded_url, "0021_restore_runtime_permissions")

    async def legacy_capacity() -> None:
        engine = create_async_engine(upgraded_url)
        async with engine.begin() as connection:
            await connection.execute(
                text("ALTER TABLE public.alembic_version ALTER COLUMN version_num TYPE VARCHAR(32)")
            )
        await engine.dispose()

    asyncio.run(legacy_capacity())
    migrate(upgraded_url, "head")

    async def assert_upgrade() -> None:
        engine = create_async_engine(upgraded_url)
        async with engine.connect() as connection:
            assert (
                await connection.scalar(text("SELECT version_num FROM public.alembic_version"))
                == "0023_recaps"
            )
            assert await connection.scalar(
                text(
                    "SELECT has_table_privilege('vgu_buddy_runtime','app_private.recaps','INSERT')"
                )
            )
            constraints = set(
                await connection.scalars(
                    text("""SELECT c.conname FROM pg_constraint c
                JOIN pg_class t ON t.oid=c.conrelid JOIN pg_namespace n ON n.oid=t.relnamespace
                WHERE n.nspname='app_private' AND t.relname IN ('recaps','recap_photos','recap_images')""")
                )
            )
            assert {
                "fk_recaps_thumbnail_owner",
                "uq_recap_photo_retry",
                "uq_recap_image_variant",
                "ck_recap_image_size",
            } <= constraints
            indexes = set(
                await connection.scalars(
                    text("SELECT indexname FROM pg_indexes WHERE schemaname='app_private'")
                )
            )
            assert {"ix_recaps_public_order", "ix_recap_photos_recap_order"} <= indexes
            policies = list(
                await connection.execute(
                    text(
                        "SELECT tablename,roles,cmd FROM pg_policies WHERE schemaname='app_private' AND tablename IN ('recaps','recap_photos','recap_images')"
                    )
                )
            )
            assert len(policies) == 3
            assert all(
                list(row.roles) == ["vgu_buddy_runtime"] and row.cmd == "ALL" for row in policies
            )
            for table in ("recaps", "recap_photos", "recap_images"):
                for role in ("anon", "authenticated", "service_role"):
                    assert not await connection.scalar(
                        text("SELECT has_table_privilege(:role,:table,'SELECT')"),
                        {"role": role, "table": "app_private." + table},
                    )
                assert not await connection.scalar(
                    text("SELECT has_table_privilege('vgu_buddy_runtime',:table,'TRUNCATE')"),
                    {"table": "app_private." + table},
                )
        await engine.dispose()

    asyncio.run(assert_upgrade())

    async def remove_disposable() -> None:
        engine = create_async_engine(url, isolation_level="AUTOCOMMIT")
        async with engine.connect() as connection:
            await connection.execute(text("DROP DATABASE " + database_name))
        await engine.dispose()

    asyncio.run(remove_disposable())


async def acceptance(url: str) -> None:
    engine = create_async_engine(url)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    actor_id, user_id = uuid4(), uuid4()
    transport = MemoryTransport()
    storage = ImageStorageService(transport)  # type: ignore[arg-type]
    async with engine.connect() as connection:
        version = await connection.scalar(text("SELECT version_num FROM public.alembic_version"))
        assert version == "0023_recaps"
        width = await connection.scalar(
            text(
                "SELECT character_maximum_length FROM information_schema.columns WHERE table_schema='public' AND table_name='alembic_version' AND column_name='version_num'"
            )
        )
        assert width == 128
        assert (
            await connection.scalar(
                text(
                    "SELECT count(*) FROM pg_tables WHERE schemaname='app_private' AND tablename IN ('recaps','recap_photos','recap_images') AND rowsecurity"
                )
            )
            == 3
        )
    async with factory() as session:
        session.add_all(
            [
                User(
                    id=actor_id,
                    email=f"{actor_id}@example.invalid",
                    password_hash="unused",
                    role=UserRole.ADMIN,
                    is_active=True,
                    email_verified=True,
                ),
                User(
                    id=user_id,
                    email=f"{user_id}@example.invalid",
                    password_hash="unused",
                    role=UserRole.USER,
                    is_active=True,
                    email_verified=True,
                ),
            ]
        )
        await session.commit()

    async def database_session() -> AsyncIterator[AsyncSession]:
        async with factory() as session:
            yield session

    key = SecretBytes(os.urandom(32))
    auth = AuthTokenSettings(signing_key=key, secure_cookies=False)
    csrf_settings = CsrfSettings(
        signing_key=key, secure_cookies=False, trusted_origins=("http://testserver",)
    )
    app.dependency_overrides[get_database_session] = database_session
    app.dependency_overrides[get_auth_token_settings] = lambda: auth
    app.dependency_overrides[get_csrf_settings] = lambda: csrf_settings
    app.dependency_overrides[get_image_storage_service] = lambda: storage

    def identity(identifier: object, role: UserRole) -> tuple[dict[str, str], dict[str, str]]:
        pair = create_token_pair(identifier, role, auth)  # type: ignore[arg-type]
        csrf = create_session_csrf_token(pair.session_id, csrf_settings)
        return {
            DEVELOPMENT_ACCESS_COOKIE_NAME: pair.access_token,
            csrf_cookie_name(csrf_settings): csrf.value,
        }, {"Origin": "http://testserver", CSRF_HEADER_NAME: csrf.value}

    cookies, headers = identity(actor_id, UserRole.ADMIN)
    source = BytesIO()
    Image.new("RGB", (1900, 1200), "green").save(source, "JPEG")
    async with (
        AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as public,
        AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://testserver",
            cookies=cookies,
            headers=headers,
        ) as admin,
    ):
        try:
            assert (await public.get("/api/admin/recaps")).status_code == 401
            user_cookies, user_headers = identity(
                user_id, UserRole.ADMIN
            )  # forged stale role claim must not grant DB role
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://testserver",
                cookies=user_cookies,
                headers=user_headers,
            ) as user:
                assert (await user.post("/api/admin/recaps", json={})).status_code == 403
            assert (
                await admin.post(
                    "/api/admin/recaps", json={}, headers={CSRF_HEADER_NAME: "invalid"}
                )
            ).status_code == 403
            created = await admin.post(
                "/api/admin/recaps",
                json={
                    "title_en": "Together",
                    "title_de": "Zusammen",
                    "summary_en": "Our memories",
                    "summary_de": "Unsere Erinnerungen",
                    "event_date": "2026-09-01",
                },
            )
            assert created.status_code == 201, created.text
            recap = created.json()
            path = "/api/admin/recaps/" + recap["id"]
            public_path = "/api/recaps/" + recap["id"]
            assert (await public.get(public_path)).status_code == 404
            assert (
                await admin.patch(
                    path + "/status", json={"version": recap["version"], "status": "PUBLISHED"}
                )
            ).status_code == 422

            async def upload(upload_id: str, version: int, data: bytes | None = None) -> Response:
                return await admin.post(
                    path + "/photos?upload_id=" + upload_id,
                    data={
                        "version": str(version),
                        "alt_en": "Friends sharing a day on campus",
                        "alt_de": "Freunde verbringen einen Tag auf dem Campus",
                    },
                    files={"file": ("photo.jpg", data or source.getvalue(), "image/jpeg")},
                )

            upload_id = str(uuid4())
            uploaded = await upload(upload_id, recap["version"])
            assert uploaded.status_code == 200, uploaded.text
            recap = uploaded.json()
            assert len(recap["photos"]) == 1 and len(transport.objects) == 2
            retry = await upload(upload_id, 1)
            assert retry.status_code == 200 and retry.json()["version"] == recap["version"]
            assert (await upload(upload_id, recap["version"], b"invalid")).status_code == 409
            assert (await admin.put(path, json={"version": 1})).status_code == 409
            second = await upload(str(uuid4()), recap["version"])
            assert second.status_code == 200
            recap = second.json()
            photos = list(reversed(recap["photos"]))
            edits = [
                {key: photo[key] for key in ("id", "alt_en", "alt_de", "caption_en", "caption_de")}
                for photo in photos
            ]
            edits[0]["caption_en"] = "<script>plain text only</script>"
            saved = await admin.put(
                path + "/photos",
                json={
                    "version": recap["version"],
                    "photos": edits,
                    "thumbnail_id": photos[0]["id"],
                },
            )
            assert saved.status_code == 200, saved.text
            recap = saved.json()
            assert recap["photos"][0]["id"] == photos[0]["id"]
            bad = await admin.put(
                path + "/photos",
                json={"version": recap["version"], "photos": edits, "thumbnail_id": str(uuid4())},
            )
            assert bad.status_code == 422
            published = await admin.patch(
                path + "/status", json={"version": recap["version"], "status": "PUBLISHED"}
            )
            assert published.status_code == 200
            recap = published.json()
            assert (await public.get(public_path)).status_code == 200
            detail = (await public.get(public_path)).json()
            assert detail["photos"][0]["caption_en"] == "<script>plain text only</script>"
            assert not any(
                key in str(detail)
                for key in ("object_key", "fingerprint", "created_by", "upload_id")
            )
            photo_url = public_path + "/photos/" + photos[0]["id"] + "/url"
            assert (await public.get(photo_url)).status_code == 200
            assert (
                await public.get(public_path + "/photos/" + str(uuid4()) + "/url")
            ).status_code == 404
            assert (await public.get(photo_url + "?variant=original")).status_code == 422
            async with factory() as session:
                references, _ = await discover_storage_references(session)
                keys = set(await session.scalars(select(RecapImage.object_key)))
                assert keys <= {ref.object_key for ref in references}
            transport.fail_upload = True
            assert (await upload(str(uuid4()), recap["version"])).status_code == 503
            transport.fail_upload = False
            assert (await admin.get(path)).json()["version"] == recap["version"]
            transport.fail_delete = True
            deletion = await admin.delete(
                path + "/photos/" + photos[0]["id"], params={"version": recap["version"]}
            )
            assert deletion.status_code == 200, deletion.text
            deleted = deletion.json()
            assert deleted["cleanup_pending"] and deleted["thumbnail_changed"]
            recap = deleted["recap"]
            assert recap["thumbnail_id"] == photos[1]["id"]
            assert (await public.get(photo_url)).status_code == 404
            transport.fail_delete = False
            clean = await admin.post(path + "/cleanup")
            assert clean.status_code == 200 and not clean.json()["cleanup_pending"]
            assert not (await admin.get(path)).json()["cleanup_pending"]
            # Related MEMBERS events cannot leak even after a previously public recap is changed.
            event_id = uuid4()
            async with factory() as session:
                session.add(
                    Event(
                        id=event_id,
                        created_by=actor_id,
                        updated_by=actor_id,
                        status=EventStatus.PUBLISHED,
                        visibility=EventVisibility.MEMBERS,
                        published_at=datetime.now(UTC),
                    )
                )
                await session.commit()
            assert (
                await admin.put(
                    path,
                    json={
                        "version": recap["version"],
                        "related_event_id": str(event_id),
                        "title_en": "A",
                        "title_de": "B",
                        "summary_en": "C",
                        "summary_de": "D",
                    },
                )
            ).status_code == 422
            linked = await admin.post("/api/admin/recaps", json={"related_event_id": str(event_id)})
            assert linked.status_code == 201
            linked_recap = linked.json()
            event_path = f"/api/admin/events/{event_id}"
            assert (await admin.delete(event_path, params={"version": 1})).status_code == 409
            assert (
                await admin.delete(
                    f"/api/admin/recaps/{linked_recap['id']}",
                    params={"version": linked_recap["version"]},
                )
            ).status_code == 200
            assert (await admin.delete(event_path, params={"version": 1})).status_code == 200
            # Pagination has no lifetime record cap; each page is stable and disjoint.
            for index in range(10):
                new = await admin.post("/api/admin/recaps", json={"title_en": f"History {index}"})
                assert new.status_code == 201
            first = (await admin.get("/api/admin/recaps")).json()
            last = (await admin.get("/api/admin/recaps?page=2")).json()
            assert len(first["items"]) == 9 and len(last["items"]) >= 2
            assert not {item["id"] for item in first["items"]} & {
                item["id"] for item in last["items"]
            }
            # Twelve-image boundary and deleted upload IDs remain inert.
            assert (
                await upload(upload_id, recap["version"])
            ).status_code == 200  # surviving photo retry
            for _ in range(11):
                response = await upload(str(uuid4()), recap["version"])
                assert response.status_code == 200, response.text
                recap = response.json()
            assert len(recap["photos"]) == 12
            assert (await upload(str(uuid4()), recap["version"])).status_code == 422
            archived = await admin.patch(
                path + "/status", json={"version": recap["version"], "status": "ARCHIVED"}
            )
            assert archived.status_code == 200
            recap = archived.json()
            assert (await public.get(public_path)).status_code == 404
            removed = await admin.delete(path, params={"version": recap["version"]})
            assert removed.status_code == 200 and not removed.json()["cleanup_pending"]
            assert (await public.get(photo_url)).status_code == 404
            assert (await admin.get(path)).status_code == 404
        finally:
            app.dependency_overrides.clear()
            await engine.dispose()
