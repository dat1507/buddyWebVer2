"""Opt-in disposable-local retention/transaction/outbox tests, never Production."""

from __future__ import annotations

import asyncio
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from typing import cast
from uuid import UUID, uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy import func, select, text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool
from test_recaps_live import MemoryTransport, local_url, migrate

from app.api.recaps import (
    public_detail,
    public_photo_url,
    retry_cleanup,
    status_recap,
    update_recap,
)
from app.models import Event, User, UserRole
from app.models.recap import Recap, RecapImage, RecapMediaCleanup, RecapPhoto
from app.schemas.recap import RecapResponse, RecapStatusUpdate, RecapUpdate
from app.services import recaps
from app.services.csrf import CsrfTokenClaims
from app.services.image_storage import (
    ImageBucket,
    ImageStorageService,
    StorageObjectRef,
    discover_storage_references,
)


@pytest.fixture
def database() -> Iterator[str]:
    base = local_url()
    name = "buddy_recap_retention_" + uuid4().hex[:8]
    url = make_url(base).set(database=name).render_as_string(hide_password=False)

    async def create() -> None:
        e = create_async_engine(base, isolation_level="AUTOCOMMIT")
        async with e.connect() as c:
            await c.execute(text("CREATE DATABASE " + name))
        await e.dispose()

    asyncio.run(create())
    migrate(url, "head")
    yield url

    async def drop() -> None:
        e = create_async_engine(base, isolation_level="AUTOCOMMIT")
        async with e.connect() as c:
            await c.execute(text("DROP DATABASE " + name))
        await e.dispose()

    asyncio.run(drop())


async def setup(
    url: str, count: int
) -> tuple[
    AsyncEngine,
    async_sessionmaker[AsyncSession],
    User,
    UUID,
    list[UUID],
    list[tuple[UUID, str]],
    MemoryTransport,
    ImageStorageService,
]:
    e = create_async_engine(url, poolclass=NullPool)
    factory = async_sessionmaker(e, expire_on_commit=False)
    transport = MemoryTransport()
    storage = ImageStorageService(transport)  # type: ignore[arg-type]
    actor = User(
        id=uuid4(),
        email=str(uuid4()) + "@example.invalid",
        password_hash="synthetic",
        role=UserRole.ADMIN,
        is_active=True,
        email_verified=True,
    )
    ids = []
    keys = []
    async with factory() as s:
        s.add(actor)
        await s.flush()
        event = Event(
            id=uuid4(),
            title_en="Never delete original Event",
            created_by=actor.id,
            updated_by=actor.id,
        )
        s.add(event)
        await s.flush()
        for i in range(count):
            r = Recap(
                id=uuid4(),
                title_en=f"Memory {i}",
                title_de=f"Erinnerung {i}",
                summary_en="Together",
                summary_de="Zusammen",
                created_by=actor.id,
                updated_by=actor.id,
                first_published_at=datetime(2026, 1, 1, tzinfo=UTC) + timedelta(seconds=i),
                status="PUBLISHED",
                version=1,
            )
            # Published related Event restriction is tested separately; keep original link on oldest
            # only for deletion-protection fixture below.
            s.add(r)
            await s.flush()
            p = RecapPhoto(
                id=uuid4(),
                recap_id=r.id,
                upload_id=uuid4(),
                fingerprint="fixture",
                alt_en="People",
                alt_de="Menschen",
                sort_order=0,
            )
            s.add(p)
            await s.flush()
            r.thumbnail_id = p.id
            for variant in ["display", "thumbnail"]:
                key = str(uuid4()) + ".webp"
                keys.append((r.id, key))
                transport.objects[key] = b"fixture"
                s.add(
                    RecapImage(
                        photo_id=p.id,
                        object_key=key,
                        variant=variant,
                        byte_size=7,
                        width=10,
                        height=10,
                    )
                )
            ids.append(r.id)
        await s.commit()
    return e, factory, actor, event.id, ids, keys, transport, storage


async def draft(
    factory: async_sessionmaker[AsyncSession],
    actor: User,
    title: str = "New memory",
    valid: bool = True,
) -> UUID:
    async with factory() as s:
        r = Recap(
            id=uuid4(),
            title_en=title,
            title_de="Neu",
            summary_en="Day",
            summary_de="Tag",
            created_by=actor.id,
            updated_by=actor.id,
            version=1,
        )
        s.add(r)
        await s.flush()
        if valid:
            p = RecapPhoto(
                id=uuid4(),
                recap_id=r.id,
                upload_id=uuid4(),
                fingerprint="new",
                alt_en="People",
                alt_de="Menschen",
                sort_order=0,
            )
            s.add(p)
            await s.flush()
            for variant in ["display", "thumbnail"]:
                s.add(
                    RecapImage(
                        photo_id=p.id,
                        object_key=str(uuid4()) + ".webp",
                        variant=variant,
                        byte_size=7,
                        width=10,
                        height=10,
                    )
                )
        await s.commit()
        return r.id


async def publish(
    factory: async_sessionmaker[AsyncSession],
    actor: User,
    storage: ImageStorageService,
    id: UUID,
    version: int = 1,
) -> RecapResponse:
    async with factory() as s:
        return await status_recap(
            id,
            RecapStatusUpdate(status="PUBLISHED", version=version),
            actor,
            cast(CsrfTokenClaims, object()),
            s,
            storage,
        )


@pytest.mark.parametrize("count", [0, 1, 8, 9, 10])
def test_boundaries_and_public_removal(database: str, count: int) -> None:
    async def check() -> None:
        e, f, a, event, ids, keys, t, storage = await setup(database, count)
        # Drafts never count, even if much older than all published rows.
        d = await draft(f, a)
        untouched = await draft(f, a, "Keep draft", valid=False)
        async with f() as s:
            assert (
                await s.scalar(
                    select(func.count()).select_from(Recap).where(Recap.status == "PUBLISHED")
                )
                == count
            )
        result = await publish(f, a, storage, d)
        removed = max(0, count + 1 - 9)
        assert [x.id for x in result.evicted_recaps] == list(reversed(ids[:removed]))
        async with f() as s:
            assert await s.get(Recap, untouched) is not None
            assert await s.get(Event, event) is not None
            assert await s.scalar(
                select(func.count()).select_from(Recap).where(Recap.status == "PUBLISHED")
            ) == min(9, count + 1)
            for old in ids[:removed]:
                assert await s.get(Recap, old) is None
                assert not await s.scalar(select(RecapPhoto.id).where(RecapPhoto.recap_id == old))
                with pytest.raises(HTTPException) as failure:
                    await public_detail(old, s)
                assert failure.value.status_code == 404
                with pytest.raises(HTTPException):
                    await public_photo_url(old, uuid4(), s, storage)
            public = await recaps.list_recaps(s, page=1, year=None, admin=False)
            assert public.total == min(9, count + 1) and len(public.items) == min(9, count + 1)
        assert all((key not in t.objects) == (rid in ids[:removed]) for rid, key in keys)
        assert result.cleanup_pending is False
        await e.dispose()

    asyncio.run(check())


def test_edit_retry_and_original_publication_clock(database: str) -> None:
    async def check() -> None:
        e, f, a, event, ids, keys, t, storage = await setup(database, 9)
        async with f() as s:
            old = await s.get(Recap, ids[0])
            assert old is not None
            timestamp = old.first_published_at
            payload = RecapUpdate(
                version=1,
                title_en="Edited",
                title_de="Neu",
                summary_en="Together",
                summary_de="Tag",
            )
            result = await update_recap(old.id, payload, a, cast(CsrfTokenClaims, object()), s)
            assert not result.evicted_recaps
        result = await publish(f, a, storage, ids[0], result.version)
        assert not result.evicted_recaps
        async with f() as s:
            restored = await s.get(Recap, ids[0])
            assert restored is not None and restored.first_published_at == timestamp
        d = await draft(f, a)
        first = await publish(f, a, storage, d)
        assert len(first.evicted_recaps) == 1
        with pytest.raises(HTTPException) as failure:
            await publish(f, a, storage, d)
        assert failure.value.status_code == 409
        again = await publish(f, a, storage, d, first.version)
        assert not again.evicted_recaps
        async with f() as s:
            assert (
                await s.scalar(
                    select(func.count()).select_from(Recap).where(Recap.status == "PUBLISHED")
                )
                == 9
            )
        await e.dispose()

    asyncio.run(check())


def test_failed_validation_and_atomic_rollback(
    database: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def check() -> None:
        e, f, a, event, ids, keys, t, storage = await setup(database, 9)
        bad = await draft(f, a, valid=False)
        with pytest.raises(HTTPException):
            await publish(f, a, storage, bad)
        d = await draft(f, a)
        real = recaps.audit

        async def fail_audit(session: AsyncSession, actor: User, recap: Recap, action: str) -> None:
            if action == "automatic_eviction":
                raise RuntimeError("injected eviction audit failure")
            await real(session, actor, recap, action)

        monkeypatch.setattr(recaps, "audit", fail_audit)
        with pytest.raises(RuntimeError):
            await publish(f, a, storage, d)
        async with f() as s:
            retained = await s.get(Recap, d)
            assert retained is not None and retained.status == "DRAFT"
            for id in ids:
                assert await s.get(Recap, id) is not None
            assert await s.scalar(select(func.count()).select_from(RecapMediaCleanup)) == 0
        assert len(t.objects) == len(keys)
        await e.dispose()

    asyncio.run(check())


def test_concurrency_and_durable_cleanup(database: str) -> None:
    async def check() -> None:
        e, f, a, event, ids, keys, t, storage = await setup(database, 9)
        async with f() as s:
            # Link to a draft Event only after publication, to prove eviction never deletes it.
            old = await s.get(Recap, ids[0])
            assert old is not None
            old.related_event_id = event
            await s.commit()
        # Other buckets/objects are never candidates; only old Recap image keys are queued.
        unrelated = str(uuid4()) + ".webp"
        t.objects[unrelated] = b"Event cover"
        first = await draft(f, a, "First")
        second = await draft(f, a, "Second")
        t.fail_delete = True
        results = await asyncio.gather(
            publish(f, a, storage, first), publish(f, a, storage, second)
        )
        assert all(r.cleanup_pending for r in results)
        assert {x.id for r in results for x in r.evicted_recaps} == set(ids[:2])
        async with f() as s:
            assert (
                await s.scalar(
                    select(func.count()).select_from(Recap).where(Recap.status == "PUBLISHED")
                )
                == 9
            )
            assert await s.get(Event, event) is not None
            assert await s.scalar(select(func.count()).select_from(RecapMediaCleanup)) == 4
            listing = await recaps.list_recaps(s, page=1, year=None, admin=True)
            assert set(listing.pending_cleanup) == set(ids[:2])
            refs, _tables = await discover_storage_references(s)
            assert StorageObjectRef(ImageBucket.EVENT_MEDIA, keys[0][1]) in refs
        t.fail_delete = False
        for old_id in ids[:2]:
            async with f() as s:
                response = await retry_cleanup(
                    old_id, a, cast(CsrfTokenClaims, object()), s, storage
                )
                assert not response.cleanup_pending
            async with f() as s:
                assert not (
                    await retry_cleanup(old_id, a, cast(CsrfTokenClaims, object()), s, storage)
                ).cleanup_pending
        assert unrelated in t.objects
        assert all(key not in t.objects for rid, key in keys if rid in ids[:2])
        async with f() as s:
            assert await s.scalar(select(func.count()).select_from(RecapMediaCleanup)) == 0
        await e.dispose()

    asyncio.run(check())


def test_timestamp_ties_use_uuid_not_event_date(database: str) -> None:
    async def check() -> None:
        e, f, a, event, ids, keys, t, storage = await setup(database, 9)
        async with f() as s:
            for id in ids:
                r = await s.get(Recap, id)
                assert r is not None
                r.first_published_at = datetime(2026, 1, 1, tzinfo=UTC)
                r.event_date = datetime(2030, 1, 1).date()
            await s.commit()
        d = await draft(f, a)
        result = await publish(f, a, storage, d)
        assert [r.id for r in result.evicted_recaps] == [min(ids)]
        await e.dispose()

    asyncio.run(check())


def test_partial_cleanup_retry_and_republication_self_eviction(
    database: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def check() -> None:
        e, f, a, event, ids, keys, t, storage = await setup(database, 9)
        d = await draft(f, a)
        calls = 0
        real = t.delete

        async def partial(reference: StorageObjectRef) -> None:
            nonlocal calls
            calls += 1
            if calls == 2:
                from app.services.image_storage import StorageOperationError

                raise StorageOperationError("synthetic interruption")
            await real(reference)

        monkeypatch.setattr(t, "delete", partial)
        result = await publish(f, a, storage, d)
        assert result.cleanup_pending
        async with f() as s:
            assert await s.get(Recap, ids[0]) is None
            assert await s.scalar(select(func.count()).select_from(RecapMediaCleanup)) == 1
            assert await s.get(Event, event) is not None
        async with f() as s:
            assert not (
                await retry_cleanup(ids[0], a, cast(CsrfTokenClaims, object()), s, storage)
            ).cleanup_pending
        # Original timestamp is retained through unpublish/republish. An older draft does not
        # displace a newer memory: it can evict itself when it is the oldest of ten.
        async with f() as s:
            r = await s.get(Recap, ids[1])
            assert r is not None
            original = r.first_published_at
            r.status = "DRAFT"
            await s.commit()
        extra = await draft(f, a)
        await publish(f, a, storage, extra)
        republished = await publish(f, a, storage, ids[1])
        assert [r.id for r in republished.evicted_recaps] == [ids[1]]
        async with f() as s:
            assert await s.get(Recap, ids[1]) is None
            assert (
                await s.scalar(
                    select(func.count()).select_from(Recap).where(Recap.status == "PUBLISHED")
                )
                == 9
            )
        assert original is not None
        await e.dispose()

    asyncio.run(check())


def test_upgrade_backfills_original_clock_and_private_cleanup_permissions() -> None:
    base = local_url()
    name = "buddy_recap_retention_upgrade_" + uuid4().hex[:8]
    url = make_url(base).set(database=name).render_as_string(hide_password=False)

    async def prepare() -> None:
        e = create_async_engine(base, isolation_level="AUTOCOMMIT")
        async with e.connect() as c:
            await c.execute(text("CREATE DATABASE " + name))
            await c.execute(
                text("""DO $$ BEGIN
                IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname='anon') THEN
                CREATE ROLE anon NOLOGIN; END IF; END $$""")
            )
        await e.dispose()

    asyncio.run(prepare())
    migrate(url, "0023_recaps")

    async def seed() -> None:
        e = create_async_engine(url)
        async with e.begin() as c:
            await c.execute(
                text(
                    "INSERT INTO app_private.users (id,email,password_hash,role) VALUES ('11111111-1111-4111-8111-111111111111','clock@example.invalid','unused','ADMIN')"
                )
            )
            await c.execute(
                text(
                    "INSERT INTO app_private.recaps (id,created_by,updated_by,status,created_at) VALUES ('22222222-2222-4222-8222-222222222222','11111111-1111-4111-8111-111111111111','11111111-1111-4111-8111-111111111111','PUBLISHED','2026-01-01T00:00:00Z')"
                )
            )
            await c.execute(
                text(
                    "INSERT INTO app_private.audit_logs (admin_id,action,resource_type,resource_id,new_value,created_at) VALUES ('11111111-1111-4111-8111-111111111111','recap.status','recap','22222222-2222-4222-8222-222222222222','{\"status\":\"PUBLISHED\"}','2026-02-01T00:00:00Z'),('11111111-1111-4111-8111-111111111111','recap.update','recap','22222222-2222-4222-8222-222222222222','{\"status\":\"PUBLISHED\"}','2026-03-01T00:00:00Z')"
                )
            )
        await e.dispose()

    asyncio.run(seed())

    async def legacy_overflow(remove: bool = False) -> None:
        e = create_async_engine(url)
        async with e.begin() as c:
            if remove:
                assert await c.scalar(text("SELECT count(*) FROM app_private.recaps")) == 11
                assert not await c.scalar(
                    text(
                        "SELECT count(*) FROM information_schema.columns WHERE table_schema='app_private' AND table_name='recaps' AND column_name='first_published_at'"
                    )
                )
                await c.execute(
                    text(
                        "DELETE FROM app_private.recaps WHERE id <> '22222222-2222-4222-8222-222222222222'"
                    )
                )
            else:
                await c.execute(
                    text(
                        "INSERT INTO app_private.recaps (id,created_by,updated_by,status) SELECT gen_random_uuid(),'11111111-1111-4111-8111-111111111111','11111111-1111-4111-8111-111111111111','PUBLISHED' FROM generate_series(1,10)"
                    )
                )
        await e.dispose()

    asyncio.run(legacy_overflow())
    with pytest.raises(Exception, match="Rolling 10 upgrade requires at most 10"):
        migrate(url, "head")
    asyncio.run(legacy_overflow(remove=True))
    migrate(url, "head")

    async def verify() -> None:
        e = create_async_engine(url)
        async with e.connect() as c:
            assert await c.scalar(
                text("SELECT first_published_at FROM app_private.recaps")
            ) == datetime(2026, 2, 1, tzinfo=UTC)
            assert await c.scalar(
                text(
                    "SELECT relrowsecurity FROM pg_class WHERE oid='app_private.recap_media_cleanup'::regclass"
                )
            )
            assert await c.scalar(
                text(
                    "SELECT has_table_privilege('vgu_buddy_runtime','app_private.recap_media_cleanup','DELETE')"
                )
            )
            assert not await c.scalar(
                text(
                    "SELECT has_table_privilege('anon','app_private.recap_media_cleanup','SELECT')"
                )
            )
        await e.dispose()
        admin = create_async_engine(base, isolation_level="AUTOCOMMIT")
        async with admin.connect() as c:
            await c.execute(text("DROP DATABASE " + name))
        await admin.dispose()

    asyncio.run(verify())


def test_storage_lost_delete_ack_then_not_found_finishes_queue(
    database: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def check() -> None:
        from app.services.image_storage import StorageOperationError

        e, f, a, event, ids, keys, t, storage = await setup(database, 9)

        async def uncertain(reference: StorageObjectRef) -> None:
            if reference.object_key not in t.objects:
                raise StorageOperationError("object already absent", status_code=404)
            t.objects.pop(reference.object_key)
            raise StorageOperationError("lost delete acknowledgement", status_code=503)

        monkeypatch.setattr(t, "delete", uncertain)
        d = await draft(f, a)
        result = await publish(f, a, storage, d)
        assert result.cleanup_pending
        async with f() as s:
            assert not (
                await retry_cleanup(ids[0], a, cast(CsrfTokenClaims, object()), s, storage)
            ).cleanup_pending
            assert await s.scalar(select(func.count()).select_from(RecapMediaCleanup)) == 0
        await e.dispose()

    asyncio.run(check())
