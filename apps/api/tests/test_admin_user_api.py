"""RBAC, audit, and response-contract tests for admin user reads."""

from __future__ import annotations

from collections.abc import AsyncIterator, Iterator
from datetime import UTC, date, datetime
from typing import cast
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID

import pytest
from httpx2 import ASGITransport, AsyncClient
from pydantic import SecretBytes
from sqlalchemy.ext.asyncio import AsyncSession

import app.api.admin_users as admin_user_api
from app.core.config import AuthTokenSettings, get_auth_token_settings
from app.core.database import get_database_session
from app.main import app
from app.models import StudentType, User, UserRole
from app.schemas.admin_user import (
    AdminProfileDetail,
    AdminProfileSummary,
    AdminUserDetail,
    AdminUserListResponse,
    AdminUserSummary,
)
from app.services.tokens import DEVELOPMENT_ACCESS_COOKIE_NAME, create_token_pair

ADMIN_ID = UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa")
USER_ID = UUID("bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb")
PROFILE_ID = UUID("cccccccc-cccc-4ccc-8ccc-cccccccccccc")
SIGNING_KEY = bytes(range(32))
CREATED_AT = datetime(2026, 9, 20, 8, 30, tzinfo=UTC)


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture(autouse=True)
def clear_dependency_overrides() -> Iterator[None]:
    app.dependency_overrides.clear()
    yield
    app.dependency_overrides.clear()


def _settings() -> AuthTokenSettings:
    return AuthTokenSettings(signing_key=SecretBytes(SIGNING_KEY), secure_cookies=False)


def _user(*, role: UserRole = UserRole.ADMIN) -> User:
    return User(
        id=ADMIN_ID,
        email="admin@example.com",
        password_hash="test-hash",
        role=role,
        is_active=True,
        email_verified=True,
    )


def _session(actor: User) -> tuple[MagicMock, AsyncSession]:
    mock = MagicMock(spec=AsyncSession)
    mock.scalar = AsyncMock(return_value=actor)
    mock.commit = AsyncMock()
    mock.rollback = AsyncMock()
    return mock, cast(AsyncSession, mock)


def _install(session: AsyncSession) -> dict[str, str]:
    settings = _settings()

    async def database_session() -> AsyncIterator[AsyncSession]:
        yield session

    app.dependency_overrides[get_database_session] = database_session
    app.dependency_overrides[get_auth_token_settings] = lambda: settings
    pair = create_token_pair(ADMIN_ID, UserRole.ADMIN, settings)
    return {DEVELOPMENT_ACCESS_COOKIE_NAME: pair.access_token}


def _summary() -> AdminUserSummary:
    return AdminUserSummary(
        id=USER_ID,
        email="student@example.com",
        role=UserRole.USER,
        is_active=True,
        email_verified=True,
        created_at=CREATED_AT,
        profile=AdminProfileSummary(
            id=PROFILE_ID,
            full_name="Ada Student",
            display_name="Ada",
            student_type=StudentType.INTERNATIONAL,
        ),
    )


def _detail() -> AdminUserDetail:
    return AdminUserDetail(
        id=USER_ID,
        email="student@example.com",
        role=UserRole.USER,
        is_active=True,
        email_verified=True,
        created_at=CREATED_AT,
        profile=AdminProfileDetail(
            id=PROFILE_ID,
            full_name="Ada Student",
            display_name="Ada",
            student_type=StudentType.INTERNATIONAL,
            nationality="German",
            major="Computer Science",
            study_year=2,
            bio="Buddy profile",
            home_university="Example University",
            arrival_date=date(2026, 9, 1),
            departure_date=date(2027, 2, 28),
            matching_opt_in=True,
            onboarding_completed_at=CREATED_AT,
        ),
    )


@pytest.mark.anyio
async def test_admin_list_passes_bounded_paging_and_search(monkeypatch: pytest.MonkeyPatch) -> None:
    actor = _user()
    mock, session = _session(actor)
    cookies = _install(session)
    service = AsyncMock(
        return_value=AdminUserListResponse(
            items=[_summary()], page=2, page_size=5, total=6, total_pages=2
        )
    )
    monkeypatch.setattr(admin_user_api, "list_admin_users", service)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver", cookies=cookies
    ) as client:
        response = await client.get("/api/admin/users?page=2&page_size=5&search=Ada")

    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    assert response.json()["items"][0]["profile"]["display_name"] == "Ada"
    service.assert_awaited_once_with(session, page=2, page_size=5, search="Ada")
    mock.commit.assert_not_awaited()
    mock.rollback.assert_not_awaited()


@pytest.mark.anyio
async def test_admin_detail_is_audited_without_profile_content(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    actor = _user()
    mock, session = _session(actor)
    cookies = _install(session)
    detail_service = AsyncMock(return_value=_detail())
    audit_service = AsyncMock()
    monkeypatch.setattr(admin_user_api, "get_admin_user_detail", detail_service)
    monkeypatch.setattr(admin_user_api, "record_audit_log", audit_service)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver", cookies=cookies
    ) as client:
        response = await client.get(f"/api/admin/users/{USER_ID}")

    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    body = response.json()
    assert body["profile"]["bio"] == "Buddy profile"
    for forbidden in ("password_hash", "preferences", "availability", "object_key", "bucket"):
        assert forbidden not in response.text
    detail_service.assert_awaited_once_with(session, USER_ID)
    audit_service.assert_awaited_once_with(
        session,
        actor,
        action="profile.admin_read",
        resource_type="student_profile",
        resource_id=USER_ID,
    )
    audit_call = audit_service.await_args
    assert audit_call is not None
    assert audit_call.kwargs.keys() == {"action", "resource_type", "resource_id"}
    mock.commit.assert_awaited_once_with()
    mock.rollback.assert_not_awaited()


@pytest.mark.anyio
@pytest.mark.parametrize("path", ["/api/admin/users", f"/api/admin/users/{USER_ID}"])
async def test_user_role_receives_403_before_admin_query(
    path: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mock, session = _session(_user(role=UserRole.USER))
    settings = _settings()

    async def database_session() -> AsyncIterator[AsyncSession]:
        yield session

    app.dependency_overrides[get_database_session] = database_session
    app.dependency_overrides[get_auth_token_settings] = lambda: settings
    pair = create_token_pair(ADMIN_ID, UserRole.ADMIN, settings)
    list_service = AsyncMock()
    detail_service = AsyncMock()
    monkeypatch.setattr(admin_user_api, "list_admin_users", list_service)
    monkeypatch.setattr(admin_user_api, "get_admin_user_detail", detail_service)

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
        cookies={DEVELOPMENT_ACCESS_COOKIE_NAME: pair.access_token},
    ) as client:
        response = await client.get(path)

    assert response.status_code == 403
    assert response.json() == {"detail": "Insufficient permissions."}
    assert response.headers["cache-control"] == "no-store"
    list_service.assert_not_awaited()
    detail_service.assert_not_awaited()


@pytest.mark.anyio
@pytest.mark.parametrize("path", ["/api/admin/users", f"/api/admin/users/{USER_ID}"])
async def test_anonymous_request_stops_before_database_access(path: str) -> None:
    database_dependency_called = False

    async def forbidden_database_session() -> AsyncSession:
        nonlocal database_dependency_called
        database_dependency_called = True
        raise AssertionError("database dependency must not run")

    app.dependency_overrides[get_database_session] = forbidden_database_session
    app.dependency_overrides[get_auth_token_settings] = _settings

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        response = await client.get(path)

    assert response.status_code == 401
    assert response.headers["cache-control"] == "no-store"
    assert database_dependency_called is False


@pytest.mark.anyio
async def test_missing_detail_is_404_and_not_audited(monkeypatch: pytest.MonkeyPatch) -> None:
    mock, session = _session(_user())
    cookies = _install(session)
    detail_service = AsyncMock(return_value=None)
    audit_service = AsyncMock()
    monkeypatch.setattr(admin_user_api, "get_admin_user_detail", detail_service)
    monkeypatch.setattr(admin_user_api, "record_audit_log", audit_service)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver", cookies=cookies
    ) as client:
        response = await client.get(f"/api/admin/users/{USER_ID}")

    assert response.status_code == 404
    assert response.json() == {"detail": "User not found."}
    assert response.headers["cache-control"] == "no-store"
    audit_service.assert_not_awaited()
    mock.commit.assert_not_awaited()


@pytest.mark.anyio
async def test_audit_failure_rolls_back_and_prevents_detail_response(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mock, session = _session(_user())
    cookies = _install(session)
    monkeypatch.setattr(admin_user_api, "get_admin_user_detail", AsyncMock(return_value=_detail()))
    monkeypatch.setattr(
        admin_user_api,
        "record_audit_log",
        AsyncMock(side_effect=RuntimeError("audit unavailable")),
    )

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver", cookies=cookies
    ) as client:
        with pytest.raises(RuntimeError, match="audit unavailable"):
            await client.get(f"/api/admin/users/{USER_ID}")

    mock.rollback.assert_awaited_once_with()
    mock.commit.assert_not_awaited()


@pytest.mark.anyio
async def test_openapi_has_read_only_routes_and_bounded_dtos() -> None:
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        document = (await client.get("/openapi.json")).json()

    assert set(document["paths"]["/api/admin/users"]) == {"get"}
    assert set(document["paths"]["/api/admin/users/{user_id}"]) == {"get"}
    schemas = document["components"]["schemas"]
    forbidden = {
        "password",
        "password_hash",
        "last_login",
        "availability",
        "preferences",
        "bucket",
        "object_key",
    }
    for schema_name in (
        "AdminProfileSummary",
        "AdminUserSummary",
        "AdminUserListResponse",
        "AdminProfileDetail",
        "AdminUserDetail",
    ):
        assert forbidden.isdisjoint(schemas[schema_name].get("properties", {}))
