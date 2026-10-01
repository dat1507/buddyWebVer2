"""RBAC, audit, and privacy tests for ADMIN matching monitoring APIs."""

from __future__ import annotations

from collections.abc import AsyncIterator, Iterator
from datetime import UTC, datetime
from typing import cast
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID

import pytest
from httpx2 import ASGITransport, AsyncClient
from pydantic import SecretBytes
from sqlalchemy.ext.asyncio import AsyncSession

import app.api.admin_matching as admin_matching_api
from app.core.config import AuthTokenSettings, get_auth_token_settings
from app.core.database import get_database_session
from app.main import app
from app.models import StudentType, User, UserRole
from app.schemas.admin_matching import (
    AdminInvitationStateCounts,
    AdminMatchingParticipantDetail,
    AdminMatchingParticipantListResponse,
    AdminMatchingParticipantSummary,
    AdminMatchingStats,
)
from app.schemas.matching import SafeInvitationProfile
from app.services.tokens import DEVELOPMENT_ACCESS_COOKIE_NAME, create_token_pair

ADMIN_ID = UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa")
PROFILE_ID = UUID("bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb")
SIGNING_KEY = bytes(range(32))
AT = datetime(2026, 10, 1, 12, 0, tzinfo=UTC)


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


def _actor(*, role: UserRole = UserRole.ADMIN) -> User:
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


def _stats() -> AdminMatchingStats:
    return AdminMatchingStats(
        participant_count=4,
        verified_participant_count=3,
        active_match_count=2,
        zero_buddy_participant_count=1,
        invitations=AdminInvitationStateCounts(
            pending=1,
            accepted=2,
            declined=3,
            cancelled=4,
            expired=5,
        ),
    )


def _summary() -> AdminMatchingParticipantSummary:
    return AdminMatchingParticipantSummary(
        profile_id=PROFILE_ID,
        display_name="Ada",
        student_type=StudentType.INTERNATIONAL,
        is_active=True,
        email_verified=True,
        matching_opt_in=True,
        buddy_count=2,
    )


def _detail() -> AdminMatchingParticipantDetail:
    return AdminMatchingParticipantDetail(
        profile=SafeInvitationProfile(
            id=PROFILE_ID,
            display_name="Ada",
            student_type=StudentType.INTERNATIONAL,
            major="Computer Science",
            avatar=None,
            interests=[],
            languages=[],
            activities=[],
            availability=None,
        ),
        is_active=True,
        email_verified=True,
        matching_opt_in=True,
        buddy_count=2,
    )


@pytest.mark.anyio
async def test_admin_reads_aggregate_stats_with_private_cache_headers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mock, session = _session(_actor())
    cookies = _install(session)
    service = AsyncMock(return_value=_stats())
    monkeypatch.setattr(admin_matching_api, "get_admin_matching_stats", service)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver", cookies=cookies
    ) as client:
        response = await client.get("/api/admin/matching/stats")

    assert response.status_code == 200
    assert response.headers["cache-control"] == "private, no-store"
    assert response.headers["pragma"] == "no-cache"
    assert response.headers["vary"] == "Cookie"
    assert response.json()["invitations"]["expired"] == 5
    service.assert_awaited_once_with(session)
    mock.commit.assert_not_awaited()


@pytest.mark.anyio
async def test_admin_participant_list_passes_only_bounded_filters(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _, session = _session(_actor())
    cookies = _install(session)
    service = AsyncMock(
        return_value=AdminMatchingParticipantListResponse(
            items=[_summary()], page=2, page_size=5, total=6, total_pages=2
        )
    )
    monkeypatch.setattr(admin_matching_api, "list_admin_matching_participants", service)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver", cookies=cookies
    ) as client:
        response = await client.get(
            "/api/admin/matching/participants",
            params={
                "page": 2,
                "page_size": 5,
                "student_type": "INTERNATIONAL",
                "verified": "true",
                "zero_buddies_only": "true",
            },
        )

    assert response.status_code == 200
    assert response.json()["items"][0] == {
        "profile_id": str(PROFILE_ID),
        "display_name": "Ada",
        "student_type": "INTERNATIONAL",
        "is_active": True,
        "email_verified": True,
        "matching_opt_in": True,
        "buddy_count": 2,
    }
    assert "email" not in response.json()["items"][0]
    service.assert_awaited_once_with(
        session,
        page=2,
        page_size=5,
        student_type=StudentType.INTERNATIONAL,
        verified=True,
        zero_buddies_only=True,
    )


@pytest.mark.anyio
async def test_admin_participant_detail_is_privacy_safe_and_audited(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    actor = _actor()
    mock, session = _session(actor)
    cookies = _install(session)
    detail_service = AsyncMock(return_value=_detail())
    audit_service = AsyncMock()
    monkeypatch.setattr(
        admin_matching_api,
        "get_admin_matching_participant_detail",
        detail_service,
    )
    monkeypatch.setattr(admin_matching_api, "record_audit_log", audit_service)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver", cookies=cookies
    ) as client:
        response = await client.get(f"/api/admin/matching/participants/{PROFILE_ID}?locale=de")

    assert response.status_code == 200
    assert response.json()["profile"]["display_name"] == "Ada"
    response_keys = set(response.json()) | set(response.json()["profile"])
    for forbidden in (
        "email",
        "user_id",
        "password",
        "message",
        "object_key",
        "bucket",
        "normalized",
    ):
        assert forbidden not in response_keys
    detail_service.assert_awaited_once_with(session, profile_id=PROFILE_ID, locale="de")
    audit_service.assert_awaited_once_with(
        session,
        actor,
        action="matching.participant_admin_read",
        resource_type="student_profile",
        resource_id=PROFILE_ID,
    )
    mock.commit.assert_awaited_once_with()
    mock.rollback.assert_not_awaited()


@pytest.mark.anyio
@pytest.mark.parametrize(
    "path",
    [
        "/api/admin/matching/stats",
        "/api/admin/matching/participants",
        f"/api/admin/matching/participants/{PROFILE_ID}",
    ],
)
async def test_user_role_is_denied_before_monitoring_queries(
    path: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _, session = _session(_actor(role=UserRole.USER))
    cookies = _install(session)
    stats_service = AsyncMock()
    list_service = AsyncMock()
    detail_service = AsyncMock()
    monkeypatch.setattr(admin_matching_api, "get_admin_matching_stats", stats_service)
    monkeypatch.setattr(admin_matching_api, "list_admin_matching_participants", list_service)
    monkeypatch.setattr(
        admin_matching_api,
        "get_admin_matching_participant_detail",
        detail_service,
    )

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver", cookies=cookies
    ) as client:
        response = await client.get(path)

    assert response.status_code == 403
    assert response.json() == {"detail": "Insufficient permissions."}
    assert response.headers["cache-control"] == "no-store"
    stats_service.assert_not_awaited()
    list_service.assert_not_awaited()
    detail_service.assert_not_awaited()


@pytest.mark.anyio
@pytest.mark.parametrize(
    "path",
    [
        "/api/admin/matching/stats",
        "/api/admin/matching/participants",
        f"/api/admin/matching/participants/{PROFILE_ID}",
    ],
)
async def test_anonymous_request_is_denied_before_database_access(path: str) -> None:
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
async def test_missing_participant_is_404_and_not_audited(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mock, session = _session(_actor())
    cookies = _install(session)
    detail_service = AsyncMock(return_value=None)
    audit_service = AsyncMock()
    monkeypatch.setattr(
        admin_matching_api,
        "get_admin_matching_participant_detail",
        detail_service,
    )
    monkeypatch.setattr(admin_matching_api, "record_audit_log", audit_service)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver", cookies=cookies
    ) as client:
        response = await client.get(f"/api/admin/matching/participants/{PROFILE_ID}")

    assert response.status_code == 404
    assert response.json() == {"detail": "Matching participant not found."}
    assert response.headers["cache-control"] == "private, no-store"
    audit_service.assert_not_awaited()
    mock.commit.assert_not_awaited()


@pytest.mark.anyio
async def test_openapi_exposes_read_only_matching_monitoring_contract() -> None:
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        document = (await client.get("/openapi.json")).json()

    paths = document["paths"]
    assert set(paths["/api/admin/matching/stats"]) == {"get"}
    assert set(paths["/api/admin/matching/participants"]) == {"get"}
    assert set(paths["/api/admin/matching/participants/{profile_id}"]) == {"get"}
    schemas = document["components"]["schemas"]
    forbidden = {
        "email",
        "user_id",
        "password_hash",
        "last_login",
        "message",
        "object_key",
        "bucket",
        "normalized_key",
    }
    for schema_name in (
        "AdminMatchingStats",
        "AdminMatchingParticipantSummary",
        "AdminMatchingParticipantListResponse",
        "AdminMatchingParticipantDetail",
    ):
        assert forbidden.isdisjoint(schemas[schema_name].get("properties", {}))
