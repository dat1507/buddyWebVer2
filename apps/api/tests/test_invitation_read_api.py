"""INV-004 HTTP authorization, ownership, privacy, and pagination tests."""

from __future__ import annotations

from collections.abc import AsyncIterator, Callable, Iterator
from datetime import UTC, date, datetime, timedelta
from typing import cast
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID

import pytest
from httpx2 import ASGITransport, AsyncClient
from pydantic import SecretBytes
from sqlalchemy.ext.asyncio import AsyncSession

import app.api.matching as matching_api
from app.api.dependencies import require_auth, require_verified_buddy_capability
from app.core.config import AuthTokenSettings, get_auth_token_settings
from app.core.database import get_database_session
from app.main import app
from app.models import (
    InvitationStatus,
    LanguageProficiency,
    StudentProfile,
    StudentType,
    User,
    UserRole,
)
from app.schemas.matching import (
    CompatibilityExplanation,
    CompatibilitySignalExplanation,
    IncomingInvitation,
    IncomingInvitationListResponse,
    SafeInvitationProfile,
    SafeMatchingAvatar,
    SafeMatchingLanguage,
    SafeMatchingPreference,
    SentInvitation,
    SentInvitationListResponse,
)
from app.services.buddy_access import VerifiedBuddyPrincipal
from app.services.invitation_reads import InvitationReadStateError

NOW = datetime(2026, 9, 29, 10, 0, tzinfo=UTC)
REFERENCE_WEEK = date(2026, 9, 28)
USER_ID = UUID("10000000-0000-4000-8000-000000000001")
PROFILE_ID = UUID("10000000-0000-4000-8000-000000000002")
OTHER_USER_ID = UUID("20000000-0000-4000-8000-000000000001")
OTHER_PROFILE_ID = UUID("20000000-0000-4000-8000-000000000002")
INVITATION_ID = UUID("30000000-0000-4000-8000-000000000001")
SIGNING_KEY = bytes(range(32))


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture(autouse=True)
def clear_dependency_overrides() -> Iterator[None]:
    app.dependency_overrides.clear()
    yield
    app.dependency_overrides.clear()


def _user(
    *,
    verified: bool = True,
    active: bool = True,
    deleted: bool = False,
) -> User:
    return User(
        id=USER_ID,
        email="private@example.com",
        password_hash="private-hash",
        role=UserRole.USER,
        is_active=active,
        email_verified=verified,
        email_verified_at=NOW if verified else None,
        deleted_at=NOW if deleted else None,
    )


def _principal() -> VerifiedBuddyPrincipal:
    return VerifiedBuddyPrincipal(
        user=_user(),
        profile=StudentProfile(
            id=PROFILE_ID,
            user_id=USER_ID,
            full_name="Current User",
            display_name="Current",
            student_type=StudentType.VIETNAMESE,
            matching_opt_in=False,
        ),
    )


def _profile() -> SafeInvitationProfile:
    return SafeInvitationProfile(
        id=OTHER_PROFILE_ID,
        display_name="Alex",
        student_type=StudentType.INTERNATIONAL,
        major="Computer Science",
        avatar=SafeMatchingAvatar(id=UUID(int=91), width=640, height=480),
        interests=[
            SafeMatchingPreference(
                id=UUID(int=92),
                code="music",
                label="Music",
                is_custom=False,
            )
        ],
        languages=[
            SafeMatchingLanguage(
                code="en",
                label="English",
                proficiency=LanguageProficiency.FLUENT,
                is_custom=False,
            )
        ],
        activities=[],
        availability=None,
    )


def _explanation() -> CompatibilityExplanation:
    return CompatibilityExplanation(
        interests=CompatibilitySignalExplanation(similarity=1, weight=40, points=40),
        activities=CompatibilitySignalExplanation(similarity=0, weight=35, points=0),
        availability=CompatibilitySignalExplanation(similarity=0, weight=15, points=0),
        languages=CompatibilitySignalExplanation(similarity=1, weight=5, points=5),
        major=CompatibilitySignalExplanation(similarity=1, weight=5, points=5),
    )


def _incoming_response() -> IncomingInvitationListResponse:
    return IncomingInvitationListResponse(
        items=[
            IncomingInvitation(
                id=INVITATION_ID,
                status=InvitationStatus.PENDING,
                created_at=NOW,
                expires_at=NOW + timedelta(days=7),
                sender=_profile(),
                message="Grüße 😀 <script>alert(1)</script>",
                score=50,
                explanation=_explanation(),
            )
        ],
        page=1,
        page_size=20,
        total=1,
        total_pages=1,
        reference_week_start=REFERENCE_WEEK,
    )


def _sent_response() -> SentInvitationListResponse:
    return SentInvitationListResponse(
        items=[
            SentInvitation(
                id=INVITATION_ID,
                status=InvitationStatus.ACCEPTED,
                created_at=NOW,
                expires_at=NOW + timedelta(days=7),
                recipient=_profile(),
                score=50,
                explanation=_explanation(),
            )
        ],
        page=1,
        page_size=20,
        total=1,
        total_pages=1,
        reference_week_start=REFERENCE_WEEK,
    )


def _session() -> tuple[MagicMock, AsyncSession]:
    mock = MagicMock(spec=AsyncSession)
    mock.commit = AsyncMock()
    mock.rollback = AsyncMock()
    return mock, cast(AsyncSession, mock)


def _install_verified(session: AsyncSession) -> VerifiedBuddyPrincipal:
    principal = _principal()

    async def database_session() -> AsyncIterator[AsyncSession]:
        yield session

    app.dependency_overrides[get_database_session] = database_session
    app.dependency_overrides[require_verified_buddy_capability] = lambda: principal
    return principal


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("view", "response_factory", "service_name"),
    (
        ("incoming", _incoming_response, "list_incoming_invitations"),
        ("sent", _sent_response, "list_sent_invitations"),
    ),
)
async def test_read_api_returns_only_private_safe_owner_page(
    view: str,
    response_factory: Callable[[], IncomingInvitationListResponse | SentInvitationListResponse],
    service_name: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mock, session = _session()
    principal = _install_verified(session)
    service = AsyncMock(return_value=response_factory())
    monkeypatch.setattr(matching_api, service_name, service)
    monkeypatch.setattr(
        matching_api,
        "current_reference_week_start",
        lambda: REFERENCE_WEEK,
    )

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        response = await client.get(
            f"/api/matching/invitations/{view}"
            f"?locale=de&page=1&page_size=20&sender_id={OTHER_USER_ID}"
            f"&recipient_id={OTHER_USER_ID}"
        )

    assert response.status_code == 200
    assert response.headers["cache-control"] == "private, no-store"
    assert response.headers["pragma"] == "no-cache"
    assert response.headers["vary"] == "Cookie"
    body = response.json()
    assert body["items"][0]["id"] == str(INVITATION_ID)
    assert body["items"][0]["score"] == 50
    assert body["reference_week_start"] == "2026-09-28"
    if view == "incoming":
        assert body["items"][0]["message"] == "Grüße 😀 <script>alert(1)</script>"
        assert body["items"][0]["sender"]["id"] == str(OTHER_PROFILE_ID)
    else:
        assert "message" not in body["items"][0]
        assert body["items"][0]["recipient"]["id"] == str(OTHER_PROFILE_ID)
    for forbidden in (
        "private@example.com",
        "private-hash",
        str(USER_ID),
        str(OTHER_USER_ID),
        "normalized_key",
        "object_key",
        "bucket",
        "outbox",
        "version",
    ):
        assert forbidden not in response.text
    service.assert_awaited_once_with(
        session,
        principal,
        locale="de",
        page=1,
        page_size=20,
        reference_week_start=REFERENCE_WEEK,
    )
    mock.commit.assert_not_awaited()
    mock.rollback.assert_not_awaited()


@pytest.mark.anyio
async def test_anonymous_read_is_rejected_before_database_or_service(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database_called = False
    service = AsyncMock()

    async def forbidden_database_session() -> AsyncSession:
        nonlocal database_called
        database_called = True
        raise AssertionError("database dependency must not run")

    app.dependency_overrides[get_database_session] = forbidden_database_session
    app.dependency_overrides[get_auth_token_settings] = lambda: AuthTokenSettings(
        signing_key=SecretBytes(SIGNING_KEY),
        secure_cookies=False,
    )
    monkeypatch.setattr(matching_api, "list_incoming_invitations", service)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        response = await client.get("/api/matching/invitations/incoming")

    assert response.status_code == 401
    assert response.headers["cache-control"] == "no-store"
    assert database_called is False
    service.assert_not_awaited()


@pytest.mark.anyio
@pytest.mark.parametrize(
    "actor",
    (_user(verified=False), _user(active=False), _user(deleted=True)),
)
async def test_unverified_inactive_or_deleted_user_cannot_read_invitations(
    actor: User,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _mock, session = _session()

    async def database_session() -> AsyncIterator[AsyncSession]:
        yield session

    app.dependency_overrides[get_database_session] = database_session
    app.dependency_overrides[require_auth] = lambda: actor
    service = AsyncMock()
    monkeypatch.setattr(matching_api, "list_incoming_invitations", service)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        response = await client.get("/api/matching/invitations/incoming")

    assert response.status_code == 403
    assert response.headers["cache-control"] == "no-store"
    service.assert_not_awaited()


@pytest.mark.anyio
@pytest.mark.parametrize("view", ("incoming", "sent"))
async def test_pagination_validation_stops_before_service(
    view: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _mock, session = _session()
    _install_verified(session)
    service = AsyncMock()
    monkeypatch.setattr(matching_api, f"list_{view}_invitations", service)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        response = await client.get(f"/api/matching/invitations/{view}?page_size=51")

    assert response.status_code == 422
    assert response.headers["cache-control"] == "no-store"
    service.assert_not_awaited()


@pytest.mark.anyio
@pytest.mark.parametrize("view", ("incoming", "sent"))
async def test_read_state_failures_are_sanitized_and_private(
    view: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _mock, session = _session()
    _install_verified(session)
    monkeypatch.setattr(
        matching_api,
        f"list_{view}_invitations",
        AsyncMock(side_effect=InvitationReadStateError("private profile id")),
    )

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        response = await client.get(f"/api/matching/invitations/{view}")

    assert response.status_code == 409
    assert response.json() == {"detail": "Invitations changed. Refresh and try again."}
    assert response.headers["cache-control"] == "private, no-store"
    assert "private profile id" not in response.text


@pytest.mark.anyio
async def test_openapi_exposes_only_bounded_read_routes_and_safe_dtos() -> None:
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        document = (await client.get("/openapi.json")).json()

    schemas = document["components"]["schemas"]
    for view, response_schema_name in (
        ("incoming", "IncomingInvitationListResponse"),
        ("sent", "SentInvitationListResponse"),
    ):
        operation = document["paths"][f"/api/matching/invitations/{view}"]["get"]
        parameters = {parameter["name"]: parameter for parameter in operation["parameters"]}
        assert parameters["page_size"]["schema"]["default"] == 20
        assert parameters["page_size"]["schema"]["maximum"] == 50
        assert operation["responses"]["200"]
        assert response_schema_name in schemas
    forbidden = {
        "email",
        "user_id",
        "sender_id",
        "recipient_id",
        "password_hash",
        "normalized_key",
        "object_key",
        "bucket",
        "version",
    }
    for schema_name in (
        "SafeInvitationProfile",
        "IncomingInvitation",
        "SentInvitation",
        "IncomingInvitationListResponse",
        "SentInvitationListResponse",
    ):
        assert forbidden.isdisjoint(schemas[schema_name].get("properties", {}))
    assert "message" in schemas["IncomingInvitation"]["properties"]
    assert "message" not in schemas["SentInvitation"]["properties"]
