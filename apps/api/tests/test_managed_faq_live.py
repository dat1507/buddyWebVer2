"""End-to-end managed FAQ acceptance against an explicitly disposable PostgreSQL server."""

import asyncio
import os
import time
from collections.abc import AsyncIterator
from typing import NoReturn
from uuid import UUID, uuid4

import pytest
from httpx2 import ASGITransport, AsyncClient
from pydantic import SecretBytes
from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from test_recaps_live import local_url, migrate

from app.core import managed_faq_cache
from app.core.config import (
    AuthTokenSettings,
    CsrfSettings,
    get_auth_token_settings,
    get_csrf_settings,
)
from app.core.database import get_database_session
from app.main import app
from app.models import User, UserRole
from app.services.chatbot.managed import answer_with_managed, baseline_service, builtin_entries
from app.services.chatbot.service import ChatbotService
from app.services.csrf import CSRF_HEADER_NAME, create_session_csrf_token, csrf_cookie_name
from app.services.tokens import DEVELOPMENT_ACCESS_COOKIE_NAME, create_token_pair

PATH = "/api/admin/knowledge-base"
ORIGIN = "http://testserver"
EN = "What is the campus origami circle?"
DE = "Was ist der Origami-Kreis am Campus?"


def content(
    en: str = EN, de: str = DE, answer: str = "Students fold paper together."
) -> dict[str, object]:
    return {
        "category": "student-life",
        "en": {"questions": [en], "answer": answer},
        "de": {"questions": [de], "answer": "Studierende falten gemeinsam Papier."},
        "source_title": "VGU campus information",
        "source_url": "https://vgu.edu.vn/",
        "evidence": "admin_managed",
    }


async def database_command(base: str, sql: str) -> None:
    engine = create_async_engine(base, isolation_level="AUTOCOMMIT")
    try:
        async with engine.connect() as connection:
            await connection.execute(text(sql))
    finally:
        await engine.dispose()


def test_managed_faq_lifecycle(monkeypatch: pytest.MonkeyPatch) -> None:
    base = local_url()  # Enforces loopback/CI host and disposable database name.
    name = "buddy_faq_test_" + uuid4().hex
    url = make_url(base).set(database=name).render_as_string(hide_password=False)
    asyncio.run(database_command(base, "CREATE DATABASE " + name))
    try:
        migrate(url, "0024_recap_retention")
        migrate(url, "0025_managed_faq")
        asyncio.run(acceptance(url, monkeypatch))
    finally:
        asyncio.run(database_command(base, "DROP DATABASE " + name))


async def acceptance(url: str, monkeypatch: pytest.MonkeyPatch) -> None:
    engine = create_async_engine(url)
    factory = async_sessionmaker(engine, expire_on_commit=False, autoflush=False)
    a_id, b_id, user_id = uuid4(), uuid4(), uuid4()
    key = SecretBytes(os.urandom(32))
    auth = AuthTokenSettings(signing_key=key, secure_cookies=False)
    csrf = CsrfSettings(signing_key=key, secure_cookies=False, trusted_origins=(ORIGIN,))
    try:
        async with factory() as s:
            assert (
                await s.scalar(text("SELECT version_num FROM public.alembic_version"))
                == "0025_managed_faq"
            )
            assert (
                await s.scalar(
                    text("""SELECT count(*) FROM pg_tables
                WHERE schemaname='app_private' AND tablename LIKE 'managed_faq%' AND rowsecurity""")
                )
                == 3
            )
            assert await s.scalar(
                text("""SELECT NOT has_table_privilege('vgu_buddy_runtime',
                'app_private.managed_faq_revision','UPDATE,DELETE')""")
            )
            for identifier, role in [
                (a_id, UserRole.ADMIN),
                (b_id, UserRole.ADMIN),
                (user_id, UserRole.USER),
            ]:
                s.add(
                    User(
                        id=identifier,
                        email=f"{identifier}@example.invalid",
                        password_hash="synthetic-only",
                        role=role,
                        is_active=True,
                    )
                )
            await s.commit()

        async def db() -> AsyncIterator[AsyncSession]:
            async with factory() as session:
                await session.execute(text("SET LOCAL ROLE vgu_buddy_runtime"))
                yield session

        app.dependency_overrides[get_database_session] = db
        app.dependency_overrides[get_auth_token_settings] = lambda: auth
        app.dependency_overrides[get_csrf_settings] = lambda: csrf
        monkeypatch.setattr(managed_faq_cache, "get_session_factory", lambda: factory)

        def client(identifier: UUID | None = None, *, with_csrf: bool = True) -> AsyncClient:
            cookies, headers = {}, {}
            if identifier:
                pair = create_token_pair(identifier, UserRole.ADMIN, auth)
                token = create_session_csrf_token(pair.session_id, csrf)
                cookies = {
                    DEVELOPMENT_ACCESS_COOKIE_NAME: pair.access_token,
                    csrf_cookie_name(csrf): token.value,
                }
                if with_csrf:
                    headers = {"Origin": ORIGIN, CSRF_HEADER_NAME: token.value}
            return AsyncClient(
                transport=ASGITransport(app=app), base_url=ORIGIN, cookies=cookies, headers=headers
            )

        async with (
            client() as public,
            client(user_id) as user,
            client(a_id, with_csrf=False) as missing,
            client(a_id) as a,
            client(b_id) as b,
        ):
            assert (await public.get(PATH)).status_code == 401
            assert (await user.post(PATH + "/preview", json={})).status_code == 403
            assert (await missing.post(PATH, json={"content": {}})).status_code == 403
            refs = await a.get(PATH + "/references")
            assert refs.status_code == 200 and len(refs.json()["builtin"]) == 17
            assert refs.headers["cache-control"] == "private, no-store"
            response = await a.post(PATH, json={"content": {}})
            assert response.status_code == 201
            record = response.json()
            assert record["status"] == "draft"
            item = PATH + "/" + record["id"]
            assert (
                await a.post(item + "/publish", json={"version": 1, "confirm": False})
            ).status_code == 422
            assert (
                await a.post(item + "/publish", json={"version": 1, "confirm": True})
            ).status_code == 422
            assert (
                await a.post(
                    PATH + "/preview",
                    content=b"x" * 131073,
                    headers={"Content-Type": "application/json"},
                )
            ).status_code == 413
            edits = await asyncio.gather(
                *(c.put(item, json={"version": 1, "content": content()}) for c in (a, b))
            )
            assert sorted(r.status_code for r in edits) == [200, 409]
            first, second = managed_faq_cache.ManagedFaqCache(), managed_faq_cache.ManagedFaqCache()
            assert not await first.get(1) and not await second.get(1)
            preview = await a.post(
                PATH + "/preview",
                json={"question": EN, "content": content(), "faq_id": record["id"]},
            )
            assert preview.json()["selected"] == "draft"
            assert preview.json()["answer"]["answer"] == "Students fold paper together."
            assert not await first.get(1) and not await second.get(1)

            services = (ChatbotService(), ChatbotService())

            async def answers(question: str) -> list[str]:
                return [
                    answer_with_managed(service, question, await worker.get(1)).answer
                    for service, worker in zip(services, (first, second), strict=True)
                ]

            async def propagate() -> None:
                await asyncio.sleep(0.17)

            assert (
                await b.post(item + "/publish", json={"version": 2, "confirm": 1})
            ).status_code == 422
            started = time.monotonic()
            pub = await b.post(item + "/publish", json={"version": 2, "confirm": True})
            assert pub.status_code == 200, pub.text
            assert pub.json()["published_revision"] == 2
            # The first publication exercises the real 15-second setting on two independent services.
            monkeypatch.setattr(managed_faq_cache, "REFRESH_SECONDS", 0.15)
            while await answers(EN) != ["Students fold paper together."] * 2:
                assert time.monotonic() - started < 25
                await asyncio.sleep(0.3)
            print(f"Both independent snapshots refreshed after {time.monotonic() - started:.2f}s")
            assert await answers(EN) == ["Students fold paper together."] * 2
            assert await answers(DE) == ["Studierende falten gemeinsam Papier."] * 2
            citation = answer_with_managed(baseline_service(), EN, await first.get(1)).sources[0]
            assert citation.verification_status == "admin_managed" and citation.verified_on is None
            assert citation.provenance is None and citation.entry_id.endswith("-r2")
            saved = await a.put(
                item, json={"version": 3, "content": content(answer="A newer draft.")}
            )
            assert saved.json()["status"] == "pending"
            await propagate()
            assert await answers(EN) == ["Students fold paper together."] * 2
            history = (await a.get(item + "/history")).json()
            assert [r["revision"] for r in history["items"]] == [4, 2, 1]
            assert history["items"][1]["author_id"] == str(a_id if edits[0].is_success else b_id)
            unpub = await a.post(item + "/unpublish", json={"version": 4, "confirm": True})
            assert unpub.json()["status"] == "unpublished"
            await propagate()
            assert "Students fold paper together." not in await answers(EN)
            restore = await b.post(
                item + "/restore",
                json={"version": 5, "revision": 2, "publish": True, "confirm": True},
            )
            assert restore.status_code == 200 and restore.json()["published_revision"] == 6
            await propagate()
            assert await answers(EN) == ["Students fold paper together."] * 2
            assert (
                await a.get(
                    PATH,
                    params={"search": "origami", "status": "published", "category": "student-life"},
                )
            ).json()["items"][0]["id"] == record["id"]
            audit = (await a.get("/api/admin/audit-logs", params={"category": "knowledge"})).json()[
                "items"
            ]
            matching = [r for r in audit if r["resource_id"] == record["id"]]
            assert len(matching) == 6
            assert next(r for r in matching if r["action"] == "knowledge.publish")[
                "admin_id"
            ] == str(b_id)
            assert "Students fold paper together." not in str(matching)

            target = next(e for e in builtin_entries() if e.id == "vgu-overview")
            replacement = content(
                target.en.questions[0], target.de.questions[0], "VGU is a university."
            )
            collision = (await a.post(PATH, json={"content": replacement})).json()
            assert (
                await a.post(
                    PATH + "/" + collision["id"] + "/publish", json={"version": 1, "confirm": True}
                )
            ).status_code == 409
            linked = (
                await a.post(PATH, json={"content": replacement, "builtin_id": target.id})
            ).json()
            linked_path = PATH + "/" + linked["id"]
            linked_pub = await a.post(
                linked_path + "/publish", json={"version": 1, "confirm": True}
            )
            assert linked_pub.status_code == 200, linked_pub.text
            await propagate()
            assert await answers(target.en.questions[0]) == ["VGU is a university."] * 2
            assert (
                await a.post(linked_path + "/unpublish", json={"version": 2, "confirm": True})
            ).status_code == 200
            await propagate()
            assert await answers(target.en.questions[0]) == [target.en.answer] * 2
            assert (
                await a.post(
                    PATH, json={"content": content(answer="Write to private@example.invalid")}
                )
            ).status_code == 422

            def unavailable() -> NoReturn:
                raise SQLAlchemyError("synthetic database outage")

            with monkeypatch.context() as outage:
                outage.setattr(managed_faq_cache, "get_session_factory", unavailable)
                outage.setattr(managed_faq_cache, "RETRY_SECONDS", 0.05)
                await propagate()
                assert not await first.get(1) and not await second.get(1)
                assert await answers(target.en.questions[0]) == [target.en.answer] * 2
            await propagate()
            assert await answers(EN) == ["Students fold paper together."] * 2

            # A malformed snapshot inserted by a privileged disposable-fixture writer is never activated.
            async with factory() as s:
                await s.execute(
                    text("""UPDATE app_private.managed_faq_revision SET content='{}'::jsonb
                    WHERE faq_id=:id AND revision=6"""),
                    {"id": UUID(record["id"])},
                )
                await s.execute(
                    text("UPDATE app_private.managed_faq_state SET generation=generation+1")
                )
                await s.commit()
            await propagate()
            assert not await first.get(1) and not await second.get(1)
    finally:
        app.dependency_overrides.clear()
        await engine.dispose()
