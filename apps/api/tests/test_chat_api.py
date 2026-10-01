"""CHAT-002 HTTP auth, privacy, CSRF, validation, and transaction tests."""

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

import app.api.chat as chat_api
from app.api.dependencies import require_session_csrf, require_verified_buddy_capability
from app.core.config import (
    AuthTokenSettings,
    CsrfSettings,
    get_auth_token_settings,
    get_csrf_settings,
)
from app.core.database import get_database_session
from app.main import app
from app.models import BuddyMessage, StudentProfile, StudentType, User, UserRole
from app.services.buddy_access import VerifiedBuddyPrincipal
from app.services.buddy_chat import (
    BuddyChatReadError,
    BuddyChatReadReason,
    BuddyMessagePage,
    BuddyMessagePersistenceError,
    BuddyMessagePersistenceReason,
)
from app.services.csrf import CsrfTokenClaims
from app.services.tokens import DEVELOPMENT_ACCESS_COOKIE_NAME, create_token_pair

NOW = datetime(2026, 10, 1, 12, 0, tzinfo=UTC)
USER_ID = UUID("10000000-0000-4000-8000-000000000001")
PROFILE_ID = UUID("20000000-0000-4000-8000-000000000001")
CONVERSATION_ID = UUID("30000000-0000-4000-8000-000000000001")
BUDDY_ID = UUID("40000000-0000-4000-8000-000000000001")
MESSAGE_ID = UUID("50000000-0000-4000-8000-000000000001")
CLIENT_MESSAGE_ID = UUID("60000000-0000-4000-8000-000000000001")


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture(autouse=True)
def clear_dependency_overrides() -> Iterator[None]:
    app.dependency_overrides.clear()
    yield
    app.dependency_overrides.clear()


def _principal() -> VerifiedBuddyPrincipal:
    user = User(
        id=USER_ID,
        email="private@example.invalid",
        password_hash="private-hash",
        role=UserRole.USER,
        is_active=True,
        email_verified=True,
        email_verified_at=NOW,
    )
    profile = StudentProfile(
        id=PROFILE_ID,
        user_id=USER_ID,
        full_name="Private Current User",
        student_type=StudentType.VIETNAMESE,
    )
    return VerifiedBuddyPrincipal(user=user, profile=profile)


def _message(*, sender_id: UUID = USER_ID, body: str = "Hello <b>Buddy</b> 😀") -> BuddyMessage:
    return BuddyMessage(
        id=MESSAGE_ID,
        conversation_id=CONVERSATION_ID,
        sender_id=sender_id,
        client_message_id=CLIENT_MESSAGE_ID,
        body=body,
        created_at=NOW,
        read_at=None,
        expires_at=NOW + timedelta(days=90),
    )


def _install(*, csrf: bool = True) -> tuple[MagicMock, AsyncSession, VerifiedBuddyPrincipal]:
    mock = MagicMock(spec=AsyncSession)
    mock.commit = AsyncMock()
    mock.rollback = AsyncMock()
    session = cast(AsyncSession, mock)

    async def database() -> AsyncIterator[AsyncSession]:
        yield session

    principal = _principal()
    app.dependency_overrides[get_database_session] = database
    app.dependency_overrides[require_verified_buddy_capability] = lambda: principal
    if csrf:
        app.dependency_overrides[require_session_csrf] = lambda: cast(CsrfTokenClaims, MagicMock())
    return mock, session, principal


@pytest.mark.anyio
async def test_history_returns_chronological_private_projection_and_cursor(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mock, session, principal = _install()
    first = _message(sender_id=BUDDY_ID, body="older")
    second = _message(body="newer")
    second.id = UUID("50000000-0000-4000-8000-000000000002")
    second.created_at = NOW + timedelta(seconds=1)
    service = AsyncMock(return_value=BuddyMessagePage((first, second), "opaque-cursor"))
    monkeypatch.setattr(chat_api, "list_buddy_messages", service)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        response = await client.get(
            f"/api/chat/conversations/{CONVERSATION_ID}/messages?before=previous&page_size=75"
        )

    assert response.status_code == 200
    assert response.headers["cache-control"] == "private, no-store"
    assert response.headers["pragma"] == "no-cache"
    assert response.headers["vary"] == "Cookie"
    assert [item["body"] for item in response.json()["items"]] == ["older", "newer"]
    assert [item["sender"] for item in response.json()["items"]] == ["buddy", "self"]
    assert response.json()["next_before"] == "opaque-cursor"
    for forbidden in (
        str(USER_ID),
        str(BUDDY_ID),
        str(CLIENT_MESSAGE_ID),
        "private@example.invalid",
        "private-hash",
        "expires_at",
        "match_id",
    ):
        assert forbidden not in response.text
    service.assert_awaited_once_with(
        session,
        conversation_id=CONVERSATION_ID,
        authenticated_user_id=principal.user.id,
        before="previous",
        page_size=75,
    )
    mock.commit.assert_not_awaited()


@pytest.mark.anyio
async def test_history_sanitizes_idor_and_invalid_cursor(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _mock, _session, _principal_value = _install()
    service = AsyncMock(
        side_effect=[
            BuddyChatReadError(BuddyChatReadReason.CONVERSATION_NOT_FOUND),
            BuddyChatReadError(BuddyChatReadReason.INVALID_CURSOR),
        ]
    )
    monkeypatch.setattr(chat_api, "list_buddy_messages", service)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        denied = await client.get(f"/api/chat/conversations/{CONVERSATION_ID}/messages")
        invalid = await client.get(
            f"/api/chat/conversations/{CONVERSATION_ID}/messages?before=invalid"
        )

    assert denied.status_code == 404
    assert denied.json() == {"detail": "CHAT_CONVERSATION_NOT_FOUND"}
    assert invalid.status_code == 422
    assert invalid.json() == {"detail": "CHAT_INVALID_CURSOR"}
    assert denied.headers["cache-control"] == "private, no-store"


@pytest.mark.anyio
async def test_send_derives_sender_commits_and_preserves_plain_text(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mock, session, principal = _install()
    message = _message(body="  <script>inert</script> 😀  ")
    service = AsyncMock(return_value=message)
    monkeypatch.setattr(chat_api, "send_buddy_message", service)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        response = await client.post(
            f"/api/chat/conversations/{CONVERSATION_ID}/messages",
            json={"client_message_id": str(CLIENT_MESSAGE_ID), "body": message.body},
        )

    assert response.status_code == 201
    assert response.json()["body"] == message.body
    assert response.json()["sender"] == "self"
    service.assert_awaited_once_with(
        session,
        conversation_id=CONVERSATION_ID,
        authenticated_sender_id=principal.user.id,
        client_message_id=CLIENT_MESSAGE_ID,
        body=message.body,
    )
    mock.commit.assert_awaited_once()
    mock.rollback.assert_not_awaited()


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("error", "status_code", "detail"),
    [
        (
            BuddyMessagePersistenceError(
                BuddyMessagePersistenceReason.ACTIVE_CONVERSATION_REQUIRED
            ),
            404,
            "CHAT_CONVERSATION_NOT_FOUND",
        ),
        (
            BuddyMessagePersistenceError(BuddyMessagePersistenceReason.IDEMPOTENCY_KEY_REUSED),
            409,
            "CHAT_IDEMPOTENCY_KEY_REUSED",
        ),
        (ValueError("must not echo body"), 422, "CHAT_MESSAGE_INVALID"),
    ],
)
async def test_send_errors_are_sanitized_and_rollback(
    error: Exception,
    status_code: int,
    detail: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mock, _session, _principal_value = _install()
    monkeypatch.setattr(chat_api, "send_buddy_message", AsyncMock(side_effect=error))

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        response = await client.post(
            f"/api/chat/conversations/{CONVERSATION_ID}/messages",
            json={"client_message_id": str(CLIENT_MESSAGE_ID), "body": "private body"},
        )

    assert response.status_code == status_code
    assert response.json() == {"detail": detail}
    assert "private body" not in response.text
    mock.rollback.assert_awaited_once()
    mock.commit.assert_not_awaited()


@pytest.mark.anyio
async def test_send_schema_enforces_unicode_boundary_and_rejects_extra_sender_field(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _mock, _session, _principal_value = _install()
    service = AsyncMock(return_value=_message())
    monkeypatch.setattr(chat_api, "send_buddy_message", service)
    url = f"/api/chat/conversations/{CONVERSATION_ID}/messages"
    maximum_body = "😀" * 10_000

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        accepted = await client.post(
            url,
            json={"client_message_id": str(CLIENT_MESSAGE_ID), "body": maximum_body},
        )
        too_long = await client.post(
            url,
            json={"client_message_id": str(CLIENT_MESSAGE_ID), "body": "😀" * 10_001},
        )
        injected = await client.post(
            url,
            json={
                "client_message_id": str(CLIENT_MESSAGE_ID),
                "body": "valid",
                "sender_id": str(BUDDY_ID),
            },
        )

    assert accepted.status_code == 201
    assert too_long.status_code == 422
    assert injected.status_code == 422
    assert service.await_count == 1
    assert service.await_args is not None
    assert service.await_args.kwargs["body"] == maximum_body


@pytest.mark.anyio
async def test_send_requires_session_csrf_before_service(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _mock, _session, _principal_value = _install(csrf=False)
    auth_settings = AuthTokenSettings(
        signing_key=SecretBytes(bytes(range(32))), secure_cookies=False
    )
    csrf_settings = CsrfSettings(
        signing_key=SecretBytes(bytes(reversed(range(32)))),
        secure_cookies=False,
        trusted_origins=("http://localhost:5173",),
    )
    app.dependency_overrides[get_auth_token_settings] = lambda: auth_settings
    app.dependency_overrides[get_csrf_settings] = lambda: csrf_settings
    token_pair = create_token_pair(USER_ID, UserRole.USER, auth_settings)
    service = AsyncMock()
    monkeypatch.setattr(chat_api, "send_buddy_message", service)

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
        cookies={DEVELOPMENT_ACCESS_COOKIE_NAME: token_pair.access_token},
    ) as client:
        response = await client.post(
            f"/api/chat/conversations/{CONVERSATION_ID}/messages",
            json={"client_message_id": str(CLIENT_MESSAGE_ID), "body": "private"},
        )

    assert response.status_code == 403
    assert response.headers["cache-control"] == "no-store"
    service.assert_not_awaited()


@pytest.mark.anyio
async def test_read_ack_commits_exact_boundary_and_returns_no_content(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mock, session, principal = _install()
    service = AsyncMock()
    monkeypatch.setattr(chat_api, "acknowledge_buddy_messages_read", service)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        response = await client.post(
            f"/api/chat/conversations/{CONVERSATION_ID}/messages/read",
            json={"through_message_id": str(MESSAGE_ID)},
        )

    assert response.status_code == 204
    assert response.content == b""
    assert response.headers["cache-control"] == "private, no-store"
    service.assert_awaited_once_with(
        session,
        conversation_id=CONVERSATION_ID,
        authenticated_reader_id=principal.user.id,
        through_message_id=MESSAGE_ID,
    )
    mock.commit.assert_awaited_once()
