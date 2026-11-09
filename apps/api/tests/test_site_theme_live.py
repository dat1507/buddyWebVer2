"""Opt-in integration check for the theme migration, role boundary and audit transaction."""

import asyncio
import os
from collections.abc import AsyncIterator
from uuid import uuid4

import pytest
from httpx2 import ASGITransport, AsyncClient
from pydantic import SecretBytes
from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from test_managed_faq_live import database_command
from test_recaps_live import migrate

from app.core.config import (
    AuthTokenSettings,
    CsrfSettings,
    get_auth_token_settings,
    get_csrf_settings,
)
from app.core.database import get_database_session
from app.main import app
from app.models import User, UserRole
from app.services.csrf import CSRF_HEADER_NAME, create_session_csrf_token, csrf_cookie_name
from app.services.tokens import DEVELOPMENT_ACCESS_COOKIE_NAME, create_token_pair

PUBLIC = "/api/public/site-theme"
ADMIN = "/api/admin/site-theme"
ORIGIN = "http://testserver"


def test_theme_publish_with_runtime_role() -> None:
    configured = os.getenv("SITE_THEME_TEST_DATABASE_URL")
    if not configured:
        pytest.skip("SITE_THEME_TEST_DATABASE_URL not configured")
    base = make_url(configured)
    if base.host not in {"localhost", "127.0.0.1"} or base.database != "buddy_theme_local":
        pytest.fail("Refusing non-disposable database")
    name = "buddy_theme_test_" + uuid4().hex
    url = base.set(database=name).render_as_string(hide_password=False)
    asyncio.run(database_command(configured, "CREATE DATABASE " + name))
    try:
        migrate(url, "0026_site_theme")
        asyncio.run(database_command(url, "UPDATE app_private.site_theme SET theme = 'summer'"))
        migrate(url, "head")
        asyncio.run(exercise(url))
    finally:
        asyncio.run(database_command(configured, "DROP DATABASE " + name))


async def exercise(url: str) -> None:
    engine = create_async_engine(url)
    factory = async_sessionmaker(engine)
    actors = {UserRole.ADMIN: uuid4(), UserRole.USER: uuid4()}
    key = SecretBytes(os.urandom(32))
    auth = AuthTokenSettings(signing_key=key, secure_cookies=False)
    csrf = CsrfSettings(signing_key=key, secure_cookies=False, trusted_origins=(ORIGIN,))

    async def db() -> AsyncIterator[AsyncSession]:
        async with factory() as session:
            await session.execute(text("SET LOCAL ROLE vgu_buddy_runtime"))
            yield session

    def client(role: UserRole | None = None, *, send_csrf: bool = True) -> AsyncClient:
        cookies: dict[str, str] = {}
        headers: dict[str, str] = {}
        if role is not None:
            pair = create_token_pair(actors[role], role, auth)
            token = create_session_csrf_token(pair.session_id, csrf)
            cookies = {
                DEVELOPMENT_ACCESS_COOKIE_NAME: pair.access_token,
                csrf_cookie_name(csrf): token.value,
            }
            if send_csrf:
                headers = {"Origin": ORIGIN, CSRF_HEADER_NAME: token.value}
        return AsyncClient(
            transport=ASGITransport(app=app), base_url=ORIGIN, cookies=cookies, headers=headers
        )

    try:
        async with factory() as session:
            for role, identifier in actors.items():
                session.add(
                    User(
                        id=identifier,
                        email=f"{identifier}@example.invalid",
                        password_hash="synthetic",
                        role=role,
                        is_active=True,
                    )
                )
            assert await session.scalar(
                text(
                    "SELECT rowsecurity FROM pg_tables "
                    "WHERE schemaname='app_private' AND tablename='site_theme'"
                )
            )
            assert not await session.scalar(
                text(
                    "SELECT has_table_privilege('vgu_buddy_runtime',"
                    "'app_private.site_theme','DELETE,TRUNCATE')"
                )
            )
            await session.commit()
        app.dependency_overrides[get_database_session] = db
        app.dependency_overrides[get_auth_token_settings] = lambda: auth
        app.dependency_overrides[get_csrf_settings] = lambda: csrf
        async with (
            client() as public,
            client(UserRole.USER) as user,
            client(UserRole.ADMIN, send_csrf=False) as no_csrf,
            client(UserRole.ADMIN) as admin,
        ):
            initial = await public.get(PUBLIC)
            assert (
                initial.json() == {"theme": "summer"}
                and initial.headers["cache-control"] == "no-store"
            )
            assert (await public.put(PUBLIC, json={"theme": "tet"})).status_code == 405
            assert (await public.get(ADMIN)).status_code == 401
            assert (await user.get(ADMIN)).status_code == 403
            assert (await user.put(ADMIN, json={"theme": "tet"})).status_code == 403
            assert (await no_csrf.put(ADMIN, json={"theme": "tet"})).status_code == 403
            assert (await admin.put(ADMIN, json={"theme": "custom"})).status_code == 422
            assert (await admin.put(ADMIN, json={"theme": "summer", "css": "x"})).status_code == 422
            for theme in (
                "default",
                "halloween",
                "christmas",
                "summer",
                "tet",
                "default",
                "default",
            ):
                published = await admin.put(ADMIN, json={"theme": theme})
                assert published.status_code == 200, published.text
                assert published.headers["cache-control"] == "private, no-store"
                assert (
                    (await public.get(PUBLIC)).json()
                    == (await admin.get(ADMIN)).json()
                    == {"theme": theme}
                )
            feed = await admin.get("/api/admin/audit-logs?category=settings")
            assert feed.status_code == 200
            assert feed.json()["total"] == 6
        async with factory() as session:
            rows = (
                await session.execute(
                    text(
                        "SELECT admin_id, old_value->>'theme' AS previous, new_value->>'theme' AS current "
                        "FROM app_private.audit_logs WHERE action='site_theme.publish' ORDER BY created_at"
                    )
                )
            ).all()
            assert [(r.admin_id, r.previous, r.current) for r in rows] == [
                (actors[UserRole.ADMIN], previous, current)
                for previous, current in zip(
                    ("summer", "default", "halloween", "christmas", "summer", "tet"),
                    ("default", "halloween", "christmas", "summer", "tet", "default"),
                    strict=True,
                )
            ]
    finally:
        app.dependency_overrides.clear()
        await engine.dispose()
