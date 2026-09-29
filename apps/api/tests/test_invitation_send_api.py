"""INV-003 API authorization, transaction, rate, and privacy tests."""

from __future__ import annotations

from collections.abc import AsyncIterator, Iterator
from datetime import UTC, datetime, timedelta
from typing import cast
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID

import pytest
from httpx2 import ASGITransport, AsyncClient
from pydantic import SecretBytes
from sqlalchemy.ext.asyncio import AsyncSession

import app.api.matching as matching_api
import app.core.rate_limits as rate_limits
from app.api.dependencies import require_auth, require_matching_eligibility
from app.core.config import (
    AuthTokenSettings,
    CsrfSettings,
    get_auth_token_settings,
    get_csrf_settings,
)
from app.core.database import get_database_session
from app.main import app
from app.models import InvitationStatus, MatchingInvitation, StudentType, User, UserRole
from app.services.csrf import CSRF_HEADER_NAME, create_session_csrf_token, csrf_cookie_name
from app.services.invitation_sending import InvitationSendError, InvitationSendReason
from app.services.matching_eligibility import EligibleMatchingPrincipal
from app.services.tokens import DEVELOPMENT_ACCESS_COOKIE_NAME, create_token_pair

NOW = datetime(2026, 9, 29, 9, 0, tzinfo=UTC)
USER_ID = UUID("10000000-0000-4000-8000-000000000001")
PROFILE_ID = UUID("10000000-0000-4000-8000-000000000002")
RECIPIENT_ID = UUID("20000000-0000-4000-8000-000000000001")
RECIPIENT_PROFILE_ID = UUID("20000000-0000-4000-8000-000000000002")
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


def _auth_settings() -> AuthTokenSettings:
    return AuthTokenSettings(signing_key=SecretBytes(SIGNING_KEY), secure_cookies=False)


def _csrf_settings() -> CsrfSettings:
    return CsrfSettings(
        signing_key=SecretBytes(SIGNING_KEY),
        secure_cookies=False,
        trusted_origins=("http://testserver",),
    )


def _user() -> User:
    return User(
        id=USER_ID,
        email="private-sender@example.com",
        password_hash="private-hash",
        role=UserRole.USER,
        is_active=True,
        email_verified=True,
        email_verified_at=NOW,
    )


def _principal() -> EligibleMatchingPrincipal:
    return EligibleMatchingPrincipal(
        user_id=USER_ID,
        profile_id=PROFILE_ID,
        student_type=StudentType.VIETNAMESE,
    )


def _invitation() -> MatchingInvitation:
    return MatchingInvitation(
        id=INVITATION_ID,
        sender_id=USER_ID,
        recipient_id=RECIPIENT_ID,
        message="private invitation text",
        status=InvitationStatus.PENDING,
        created_at=NOW,
        updated_at=NOW,
        expires_at=NOW + timedelta(days=7),
    )


def _session() -> tuple[MagicMock, AsyncSession]:
    mock = MagicMock(spec=AsyncSession)
    mock.commit = AsyncMock()
    mock.rollback = AsyncMock()
    return mock, cast(AsyncSession, mock)


def _install(session: AsyncSession) -> tuple[dict[str, str], dict[str, str]]:
    auth_settings = _auth_settings()
    csrf_settings = _csrf_settings()

    async def database_session() -> AsyncIterator[AsyncSession]:
        yield session

    app.dependency_overrides[get_database_session] = database_session
    app.dependency_overrides[get_auth_token_settings] = lambda: auth_settings
    app.dependency_overrides[get_csrf_settings] = lambda: csrf_settings
    app.dependency_overrides[require_auth] = _user
    app.dependency_overrides[require_matching_eligibility] = _principal
    pair = create_token_pair(USER_ID, UserRole.USER, auth_settings)
    csrf = create_session_csrf_token(pair.session_id, csrf_settings)
    cookies = {
        DEVELOPMENT_ACCESS_COOKIE_NAME: pair.access_token,
        csrf_cookie_name(csrf_settings): csrf.value,
    }
    headers = {"Origin": "http://testserver", CSRF_HEADER_NAME: csrf.value}
    return cookies, headers


@pytest.mark.anyio
async def test_create_invitation_commits_once_and_returns_minimal_private_receipt(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mock, session = _session()
    cookies, headers = _install(session)
    service = AsyncMock(return_value=_invitation())
    monkeypatch.setattr(matching_api, "send_matching_invitation", service)

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
        cookies=cookies,
    ) as client:
        response = await client.post(
            "/api/matching/invitations",
            headers=headers,
            json={
                "recipient_profile_id": str(RECIPIENT_PROFILE_ID),
                "message": "  Hello  ",
            },
        )

    assert response.status_code == 201
    assert response.json() == {
        "id": str(INVITATION_ID),
        "status": "PENDING",
        "expires_at": "2026-10-06T09:00:00Z",
    }
    assert response.headers["cache-control"] == "private, no-store"
    assert response.headers["pragma"] == "no-cache"
    assert response.headers["vary"] == "Cookie"
    for forbidden in (
        "private-sender@example.com",
        "private-hash",
        "private invitation text",
        str(USER_ID),
        str(RECIPIENT_ID),
    ):
        assert forbidden not in response.text
    service.assert_awaited_once_with(
        session,
        _principal(),
        recipient_profile_id=RECIPIENT_PROFILE_ID,
        message="  Hello  ",
    )
    mock.commit.assert_awaited_once_with()
    mock.rollback.assert_not_awaited()


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("reason", "expected_status"),
    (
        (InvitationSendReason.MESSAGE_TOO_MANY_WORDS, 422),
        (InvitationSendReason.MESSAGE_TOO_MANY_CODE_POINTS, 422),
        (InvitationSendReason.SELF_NOT_ALLOWED, 422),
        (InvitationSendReason.PENDING_EXISTS, 409),
        (InvitationSendReason.PENDING_LIMIT_REACHED, 409),
        (InvitationSendReason.ACTIVE_PAIR_EXISTS, 409),
        (InvitationSendReason.SENDER_INELIGIBLE, 409),
        (InvitationSendReason.RECIPIENT_INELIGIBLE, 409),
    ),
)
async def test_domain_rejections_are_stable_sanitized_and_rolled_back(
    reason: InvitationSendReason,
    expected_status: int,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mock, session = _session()
    cookies, headers = _install(session)
    monkeypatch.setattr(
        matching_api,
        "send_matching_invitation",
        AsyncMock(side_effect=InvitationSendError(reason)),
    )

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
        cookies=cookies,
    ) as client:
        response = await client.post(
            "/api/matching/invitations",
            headers=headers,
            json={
                "recipient_profile_id": str(RECIPIENT_PROFILE_ID),
                "message": "private submitted value",
            },
        )

    assert response.status_code == expected_status
    assert response.json() == {"detail": reason.value}
    assert response.headers["cache-control"] == "private, no-store"
    assert "private submitted value" not in response.text
    mock.rollback.assert_awaited_once_with()
    mock.commit.assert_not_awaited()


@pytest.mark.anyio
async def test_invitation_mutation_requires_session_csrf_before_service(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _mock, session = _session()
    cookies, _headers = _install(session)
    service = AsyncMock()
    monkeypatch.setattr(matching_api, "send_matching_invitation", service)

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
        cookies=cookies,
    ) as client:
        response = await client.post(
            "/api/matching/invitations",
            headers={"Origin": "http://testserver"},
            json={
                "recipient_profile_id": str(RECIPIENT_PROFILE_ID),
                "message": "Hello",
            },
        )

    assert response.status_code == 403
    assert response.json() == {"detail": "CSRF validation failed."}
    service.assert_not_awaited()


@pytest.mark.anyio
async def test_invitation_route_is_ip_rate_limited_before_second_mutation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _mock, session = _session()
    cookies, headers = _install(session)
    service = AsyncMock(return_value=_invitation())
    monkeypatch.setattr(matching_api, "send_matching_invitation", service)
    monkeypatch.setattr(rate_limits, "USER_REQUESTS_PER_MINUTE", 1)

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
        cookies=cookies,
    ) as client:
        first = await client.post(
            "/api/matching/invitations",
            headers=headers,
            json={"recipient_profile_id": str(RECIPIENT_PROFILE_ID), "message": "Hello"},
        )
        second = await client.post(
            "/api/matching/invitations",
            headers=headers,
            json={"recipient_profile_id": str(RECIPIENT_PROFILE_ID), "message": "Hello"},
        )

    assert first.status_code == 201
    assert second.status_code == 429
    assert second.headers["cache-control"] == "no-store"
    service.assert_awaited_once()


@pytest.mark.anyio
async def test_invitation_route_is_user_rate_limited_before_second_mutation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _mock, session = _session()
    cookies, headers = _install(session)
    service = AsyncMock(return_value=_invitation())
    monkeypatch.setattr(matching_api, "send_matching_invitation", service)
    monkeypatch.setattr(rate_limits, "USER_REQUESTS_PER_MINUTE", 1)
    monkeypatch.setattr(rate_limits.AuthRateLimiter, "check_ip", AsyncMock())

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
        cookies=cookies,
    ) as client:
        first = await client.post(
            "/api/matching/invitations",
            headers=headers,
            json={"recipient_profile_id": str(RECIPIENT_PROFILE_ID), "message": "Hello"},
        )
        second = await client.post(
            "/api/matching/invitations",
            headers=headers,
            json={"recipient_profile_id": str(RECIPIENT_PROFILE_ID), "message": "Hello"},
        )

    assert first.status_code == 201
    assert second.status_code == 429
    assert second.headers["cache-control"] == "no-store"
    service.assert_awaited_once()


@pytest.mark.anyio
async def test_openapi_documents_bounded_plain_text_request_and_minimal_response() -> None:
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        document = (await client.get("/openapi.json")).json()

    operation = document["paths"]["/api/matching/invitations"]["post"]
    request_schema = document["components"]["schemas"]["InvitationCreateRequest"]
    response_schema = document["components"]["schemas"]["InvitationCreateResponse"]
    assert operation["responses"]["201"]
    assert "500 maximal non-whitespace runs" in request_schema["properties"]["message"][
        "description"
    ]
    assert set(response_schema["properties"]) == {"id", "status", "expires_at"}
    forbidden = {"email", "user_id", "recipient_id", "sender_id", "message"}
    assert forbidden.isdisjoint(response_schema["properties"])
