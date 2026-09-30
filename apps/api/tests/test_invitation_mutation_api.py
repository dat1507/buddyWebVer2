"""INV-006 mutation API ownership, CSRF, transaction, and privacy tests."""

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

import app.api.matching as matching_api
from app.api.dependencies import require_auth, require_verified_buddy_capability
from app.core.config import (
    AuthTokenSettings,
    CsrfSettings,
    get_auth_token_settings,
    get_csrf_settings,
)
from app.core.database import get_database_session
from app.main import app
from app.models import InvitationStatus, StudentProfile, StudentType, User, UserRole
from app.services.buddy_access import VerifiedBuddyPrincipal
from app.services.csrf import CSRF_HEADER_NAME, create_session_csrf_token, csrf_cookie_name
from app.services.invitation_mutations import (
    InvitationMutationError,
    InvitationMutationReason,
    InvitationMutationResult,
)
from app.services.tokens import DEVELOPMENT_ACCESS_COOKIE_NAME, create_token_pair

NOW = datetime(2026, 9, 30, 16, 0, tzinfo=UTC)
OWNER_USER_ID = UUID("20000000-0000-4000-8000-000000000001")
OWNER_PROFILE_ID = UUID("20000000-0000-4000-8000-000000000002")
INVITATION_ID = UUID("30000000-0000-4000-8000-000000000001")
SIGNING_KEY = bytes(range(32))

ACTION_CASES = (
    ("decline", "decline_matching_invitation", InvitationStatus.DECLINED),
    ("cancel", "cancel_matching_invitation", InvitationStatus.CANCELLED),
    ("hide", "hide_accepted_invitation_from_sender", InvitationStatus.ACCEPTED),
)


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


def _user(*, verified: bool = True) -> User:
    return User(
        id=OWNER_USER_ID,
        email="private-owner@example.com",
        password_hash="private-test-hash",
        role=UserRole.USER,
        is_active=True,
        email_verified=verified,
        email_verified_at=NOW if verified else None,
    )


def _profile() -> StudentProfile:
    return StudentProfile(
        id=OWNER_PROFILE_ID,
        user_id=OWNER_USER_ID,
        full_name="Private Owner",
        student_type=StudentType.INTERNATIONAL,
    )


def _principal() -> VerifiedBuddyPrincipal:
    return VerifiedBuddyPrincipal(user=_user(), profile=_profile())


def _session() -> tuple[MagicMock, AsyncSession]:
    mock = MagicMock(spec=AsyncSession)
    mock.scalar = AsyncMock()
    mock.commit = AsyncMock()
    mock.rollback = AsyncMock()
    return mock, cast(AsyncSession, mock)


def _install(
    session: AsyncSession,
    *,
    override_verified: bool = True,
) -> tuple[dict[str, str], dict[str, str]]:
    auth_settings = _auth_settings()
    csrf_settings = _csrf_settings()

    async def database_session() -> AsyncIterator[AsyncSession]:
        yield session

    app.dependency_overrides[get_database_session] = database_session
    app.dependency_overrides[get_auth_token_settings] = lambda: auth_settings
    app.dependency_overrides[get_csrf_settings] = lambda: csrf_settings
    app.dependency_overrides[require_auth] = _user
    if override_verified:
        app.dependency_overrides[require_verified_buddy_capability] = _principal
    pair = create_token_pair(OWNER_USER_ID, UserRole.USER, auth_settings)
    csrf = create_session_csrf_token(pair.session_id, csrf_settings)
    cookies = {
        DEVELOPMENT_ACCESS_COOKIE_NAME: pair.access_token,
        csrf_cookie_name(csrf_settings): csrf.value,
    }
    headers = {"Origin": "http://testserver", CSRF_HEADER_NAME: csrf.value}
    return cookies, headers


@pytest.mark.anyio
@pytest.mark.parametrize(("action", "service_name", "expected_status"), ACTION_CASES)
async def test_mutation_commits_once_and_returns_minimal_receipt(
    action: str,
    service_name: str,
    expected_status: InvitationStatus,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mock, session = _session()
    cookies, headers = _install(session)
    service = AsyncMock(
        return_value=InvitationMutationResult(
            invitation_id=INVITATION_ID,
            status=expected_status,
        )
    )
    monkeypatch.setattr(matching_api, service_name, service)

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
        cookies=cookies,
    ) as client:
        response = await client.post(
            f"/api/matching/invitations/{INVITATION_ID}/{action}",
            headers=headers,
        )

    assert response.status_code == 200
    assert response.json() == {
        "invitation_id": str(INVITATION_ID),
        "status": expected_status.value,
    }
    assert response.headers["cache-control"] == "private, no-store"
    assert response.headers["pragma"] == "no-cache"
    assert response.headers["vary"] == "Cookie"
    for forbidden in (
        "private-owner@example.com",
        "private-test-hash",
        "message",
        str(OWNER_USER_ID),
        str(OWNER_PROFILE_ID),
        "match_id",
        "conversation_id",
    ):
        assert forbidden not in response.text
    service.assert_awaited_once()
    assert service.await_args is not None
    assert service.await_args.args[0] is session
    assert service.await_args.args[1].user.id == OWNER_USER_ID
    assert service.await_args.kwargs == {"invitation_id": INVITATION_ID}
    mock.commit.assert_awaited_once_with()
    mock.rollback.assert_not_awaited()


@pytest.mark.anyio
@pytest.mark.parametrize(("action", "service_name", "_status"), ACTION_CASES)
@pytest.mark.parametrize("reason", tuple(InvitationMutationReason))
async def test_mutation_errors_are_stable_private_and_rolled_back(
    action: str,
    service_name: str,
    _status: InvitationStatus,
    reason: InvitationMutationReason,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mock, session = _session()
    cookies, headers = _install(session)
    monkeypatch.setattr(
        matching_api,
        service_name,
        AsyncMock(side_effect=InvitationMutationError(reason)),
    )

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
        cookies=cookies,
    ) as client:
        response = await client.post(
            f"/api/matching/invitations/{INVITATION_ID}/{action}",
            headers=headers,
        )

    expected_status = 404 if reason is InvitationMutationReason.NOT_FOUND else 409
    assert response.status_code == expected_status
    assert response.json() == {"detail": reason.value}
    assert response.headers["cache-control"] == "private, no-store"
    assert "sql" not in response.text.casefold()
    assert "constraint" not in response.text.casefold()
    assert "lock" not in response.text.casefold()
    mock.rollback.assert_awaited_once_with()
    mock.commit.assert_not_awaited()


@pytest.mark.anyio
@pytest.mark.parametrize(("action", "service_name", "_status"), ACTION_CASES)
async def test_mutation_requires_session_csrf_before_service(
    action: str,
    service_name: str,
    _status: InvitationStatus,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _mock, session = _session()
    cookies, _headers = _install(session)
    service = AsyncMock()
    monkeypatch.setattr(matching_api, service_name, service)

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
        cookies=cookies,
    ) as client:
        response = await client.post(
            f"/api/matching/invitations/{INVITATION_ID}/{action}",
            headers={"Origin": "http://testserver"},
        )

    assert response.status_code == 403
    assert response.json() == {"detail": "CSRF validation failed."}
    service.assert_not_awaited()


@pytest.mark.anyio
@pytest.mark.parametrize(("action", "service_name", "_status"), ACTION_CASES)
async def test_mutation_requires_authenticated_verified_owner(
    action: str,
    service_name: str,
    _status: InvitationStatus,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mock, session = _session()
    service = AsyncMock()
    monkeypatch.setattr(matching_api, service_name, service)

    async def database_session() -> AsyncIterator[AsyncSession]:
        yield session

    app.dependency_overrides[get_database_session] = database_session
    app.dependency_overrides[get_auth_token_settings] = _auth_settings
    app.dependency_overrides[get_csrf_settings] = _csrf_settings
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as client:
        anonymous = await client.post(f"/api/matching/invitations/{INVITATION_ID}/{action}")
    assert anonymous.status_code == 401

    app.dependency_overrides.clear()
    cookies, headers = _install(session, override_verified=False)
    app.dependency_overrides[require_auth] = lambda: _user(verified=False)
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
        cookies=cookies,
    ) as client:
        unverified = await client.post(
            f"/api/matching/invitations/{INVITATION_ID}/{action}",
            headers=headers,
        )
    assert unverified.status_code == 403
    assert unverified.json() == {"detail": "EMAIL_VERIFICATION_REQUIRED"}
    service.assert_not_awaited()
    mock.scalar.assert_not_awaited()


@pytest.mark.anyio
@pytest.mark.parametrize(("action", "service_name", "_status"), ACTION_CASES)
async def test_unexpected_mutation_failure_rolls_back(
    action: str,
    service_name: str,
    _status: InvitationStatus,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mock, session = _session()
    cookies, headers = _install(session)
    monkeypatch.setattr(
        matching_api,
        service_name,
        AsyncMock(side_effect=RuntimeError("injected failure")),
    )

    with pytest.raises(RuntimeError, match="injected failure"):
        async with AsyncClient(
            transport=ASGITransport(app=app, raise_app_exceptions=True),
            base_url="http://testserver",
            cookies=cookies,
        ) as client:
            await client.post(
                f"/api/matching/invitations/{INVITATION_ID}/{action}",
                headers=headers,
            )
    mock.rollback.assert_awaited_once_with()
    mock.commit.assert_not_awaited()


def test_openapi_documents_bodyless_mutations_and_minimal_shared_response() -> None:
    openapi = app.openapi()
    for action, _service_name, _status in ACTION_CASES:
        operation = openapi["paths"][f"/api/matching/invitations/{{invitation_id}}/{action}"][
            "post"
        ]
        assert "requestBody" not in operation
        assert operation["parameters"] == [
            {
                "name": "invitation_id",
                "in": "path",
                "required": True,
                "schema": {"type": "string", "format": "uuid", "title": "Invitation Id"},
            }
        ]
    response_schema = openapi["components"]["schemas"]["InvitationMutationResponse"]
    assert set(response_schema["properties"]) == {"invitation_id", "status"}
