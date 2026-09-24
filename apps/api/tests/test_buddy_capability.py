"""HTTP/WebSocket permission matrix for the shared VERIFIED Buddy guard."""

from __future__ import annotations

from collections.abc import AsyncIterator, Callable
from datetime import UTC, datetime
from typing import Annotated, cast
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID

import pytest
from fastapi import Depends, FastAPI, WebSocket
from fastapi.testclient import TestClient
from httpx2 import ASGITransport, AsyncClient
from pydantic import SecretBytes
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.websockets import WebSocketDisconnect

from app.api.dependencies import (
    AUTHENTICATION_REQUIRED_MESSAGE,
    AUTHORIZATION_REQUIRED_MESSAGE,
    require_verified_buddy_capability,
    require_verified_buddy_websocket,
)
from app.core.config import AuthTokenSettings, get_auth_token_settings
from app.core.database import get_database_session
from app.models import StudentProfile, User, UserRole
from app.schemas.profile_completion import MatchingIneligibilityReason
from app.services.buddy_access import (
    BuddyCapabilityError,
    VerifiedBuddyPrincipal,
    get_verified_buddy_principal,
)
from app.services.tokens import DEVELOPMENT_ACCESS_COOKIE_NAME, create_token_pair

USER_ID = UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa")
OTHER_USER_ID = UUID("bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb")
PROFILE_ID = UUID("cccccccc-cccc-4ccc-8ccc-cccccccccccc")
NOW = datetime(2026, 9, 24, 12, 0, tzinfo=UTC)
SIGNING_KEY = bytes(range(32))


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


def _settings() -> AuthTokenSettings:
    return AuthTokenSettings(signing_key=SecretBytes(SIGNING_KEY), secure_cookies=False)


def _user(
    *,
    role: UserRole = UserRole.USER,
    verified: bool = True,
    is_active: bool = True,
    deleted: bool = False,
) -> User:
    return User(
        id=USER_ID,
        email="student@example.com",
        password_hash="test-hash",
        role=role,
        is_active=is_active,
        email_verified=True,
        email_verified_at=NOW if verified else None,
        deleted_at=NOW if deleted else None,
    )


def _profile(*, user_id: UUID = USER_ID, deleted: bool = False) -> StudentProfile:
    return StudentProfile(
        id=PROFILE_ID,
        user_id=user_id,
        matching_opt_in=True,
        version=1,
        deleted_at=NOW if deleted else None,
    )


def _session(*results: object) -> tuple[MagicMock, AsyncSession]:
    mock = MagicMock(spec=AsyncSession)
    mock.scalar = AsyncMock(side_effect=results)
    return mock, cast(AsyncSession, mock)


def _cookie(role: UserRole = UserRole.USER) -> dict[str, str]:
    token = create_token_pair(USER_ID, role, _settings()).access_token
    return {DEVELOPMENT_ACCESS_COOKIE_NAME: token}


def _probe_app(
    session_dependency: Callable[..., object],
    protected_query: AsyncMock,
) -> FastAPI:
    probe = FastAPI()
    probe.dependency_overrides[get_database_session] = session_dependency
    probe.dependency_overrides[get_auth_token_settings] = _settings

    @probe.get("/buddy")
    async def buddy_route(
        principal: Annotated[
            VerifiedBuddyPrincipal,
            Depends(require_verified_buddy_capability),
        ],
    ) -> dict[str, str]:
        await protected_query()
        return {
            "user_id": str(principal.user.id),
            "profile_id": str(principal.profile.id),
        }

    @probe.websocket("/buddy-ws")
    async def buddy_socket(
        websocket: WebSocket,
        principal: Annotated[
            VerifiedBuddyPrincipal,
            Depends(require_verified_buddy_websocket),
        ],
    ) -> None:
        await protected_query()
        await websocket.accept()
        await websocket.send_json(
            {
                "user_id": str(principal.user.id),
                "profile_id": str(principal.profile.id),
            }
        )
        await websocket.close()

    return probe


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("actor", "profile", "expected_status", "expected_detail", "scalar_calls"),
    [
        (_user(verified=False), None, 403, "EMAIL_VERIFICATION_REQUIRED", 1),
        (_user(role=UserRole.ADMIN), None, 403, AUTHORIZATION_REQUIRED_MESSAGE, 1),
        (_user(is_active=False), None, 401, AUTHENTICATION_REQUIRED_MESSAGE, 1),
        (_user(deleted=True), None, 401, AUTHENTICATION_REQUIRED_MESSAGE, 1),
        (_user(), None, 403, AUTHORIZATION_REQUIRED_MESSAGE, 2),
        (_user(), _profile(user_id=OTHER_USER_ID), 403, AUTHORIZATION_REQUIRED_MESSAGE, 2),
        (_user(), _profile(deleted=True), 403, AUTHORIZATION_REQUIRED_MESSAGE, 2),
        (_user(), _profile(), 200, None, 2),
    ],
)
async def test_http_guard_permission_matrix_runs_before_protected_query(
    actor: User,
    profile: StudentProfile | None,
    expected_status: int,
    expected_detail: str | None,
    scalar_calls: int,
) -> None:
    results: list[object] = [actor]
    if scalar_calls == 2:
        results.append(profile)
    mock, session = _session(*results)
    protected_query = AsyncMock()

    async def database_session() -> AsyncIterator[AsyncSession]:
        yield session

    probe = _probe_app(database_session, protected_query)
    async with AsyncClient(
        transport=ASGITransport(app=probe),
        base_url="http://testserver",
        cookies=_cookie(actor.role),
    ) as client:
        response = await client.get(f"/buddy?profile_id={OTHER_USER_ID}")

    assert response.status_code == expected_status
    assert mock.scalar.await_count == scalar_calls
    if expected_status == 200:
        assert response.json() == {
            "user_id": str(USER_ID),
            "profile_id": str(PROFILE_ID),
        }
        protected_query.assert_awaited_once_with()
        profile_statement = mock.scalar.await_args_list[1].args[0]
        compiled = profile_statement.compile(
            dialect=make_url("postgresql+asyncpg://").get_dialect()()
        )
        assert USER_ID in compiled.params.values()
        assert OTHER_USER_ID not in compiled.params.values()
        assert "student_profiles.deleted_at IS NULL" in str(compiled)
    else:
        assert response.json() == {"detail": expected_detail}
        assert response.headers["cache-control"] == "no-store"
        protected_query.assert_not_awaited()


@pytest.mark.anyio
async def test_anonymous_http_guard_stops_before_database_and_protected_query() -> None:
    mock, session = _session()
    protected_query = AsyncMock()

    async def database_session() -> AsyncIterator[AsyncSession]:
        yield session

    probe = _probe_app(database_session, protected_query)
    async with AsyncClient(
        transport=ASGITransport(app=probe),
        base_url="http://testserver",
    ) as client:
        response = await client.get("/buddy")

    assert response.status_code == 401
    mock.scalar.assert_not_awaited()
    protected_query.assert_not_awaited()


@pytest.mark.anyio
async def test_preserved_profile_unlocks_after_timestamp_verification() -> None:
    user = _user(verified=False)
    profile = _profile()
    mock, session = _session(profile)

    with pytest.raises(BuddyCapabilityError) as denied:
        await get_verified_buddy_principal(session, user)
    assert denied.value.reason is MatchingIneligibilityReason.EMAIL_VERIFICATION_REQUIRED
    mock.scalar.assert_not_awaited()

    user.email_verified_at = NOW
    principal = await get_verified_buddy_principal(session, user)

    assert principal.user is user
    assert principal.profile is profile
    assert profile.deleted_at is None
    assert "student@example.com" not in repr(principal)


def test_websocket_guard_rejects_anonymous_before_database_access() -> None:
    mock, session = _session()
    protected_query = AsyncMock()

    async def database_session() -> AsyncIterator[AsyncSession]:
        yield session

    probe = _probe_app(database_session, protected_query)
    with TestClient(probe) as client:
        with pytest.raises(WebSocketDisconnect) as denied:
            with client.websocket_connect("/buddy-ws"):
                pass

    assert denied.value.code == 1008
    assert denied.value.reason == AUTHENTICATION_REQUIRED_MESSAGE
    mock.scalar.assert_not_awaited()
    protected_query.assert_not_awaited()


@pytest.mark.parametrize(
    ("actor", "results", "reason"),
    [
        (_user(verified=False), [], "EMAIL_VERIFICATION_REQUIRED"),
        (_user(role=UserRole.ADMIN), [], AUTHORIZATION_REQUIRED_MESSAGE),
        (_user(), [None], AUTHORIZATION_REQUIRED_MESSAGE),
    ],
)
def test_websocket_guard_denies_before_socket_handler(
    actor: User,
    results: list[object],
    reason: str,
) -> None:
    mock, session = _session(actor, *results)
    protected_query = AsyncMock()

    async def database_session() -> AsyncIterator[AsyncSession]:
        yield session

    probe = _probe_app(database_session, protected_query)
    with TestClient(probe) as client:
        client.cookies.update(_cookie(actor.role))
        with pytest.raises(WebSocketDisconnect) as denied:
            with client.websocket_connect("/buddy-ws"):
                pass

    assert denied.value.code == 1008
    assert denied.value.reason == reason
    protected_query.assert_not_awaited()


def test_websocket_guard_allows_verified_owned_profile() -> None:
    mock, session = _session(_user(), _profile())
    protected_query = AsyncMock()

    async def database_session() -> AsyncIterator[AsyncSession]:
        yield session

    probe = _probe_app(database_session, protected_query)
    with TestClient(probe) as client:
        client.cookies.update(_cookie())
        with client.websocket_connect("/buddy-ws") as socket:
            assert socket.receive_json() == {
                "user_id": str(USER_ID),
                "profile_id": str(PROFILE_ID),
            }

    assert mock.scalar.await_count == 2
    protected_query.assert_awaited_once_with()
