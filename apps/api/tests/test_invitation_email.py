"""INV-008 current-address resolution and plain-text template tests."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import cast
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID

import pytest
from pydantic import SecretBytes
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import EmailVerificationDeliverySettings
from app.services.email_outbox import (
    EmailTemplateError,
    default_email_delivery_resolver_registry,
    default_email_template_registry,
)
from app.services.invitation_email import (
    MatchingInvitationCreatedResolver,
    MatchingInvitationCreatedTemplate,
)
from app.services.invitation_sending import MATCHING_INVITATION_CREATED

INVITATION_ID = UUID("11111111-1111-4111-8111-111111111111")
RECIPIENT_ID = UUID("22222222-2222-4222-8222-222222222222")
SETTINGS = EmailVerificationDeliverySettings(
    public_app_base_url="https://staging.vgubuddyprogram.com",
    sealing_key=SecretBytes(bytes(range(32))),
)


def _session(result: tuple[str, str | None] | None) -> tuple[MagicMock, AsyncSession]:
    mock = MagicMock(spec=AsyncSession)
    execution = MagicMock()
    execution.one_or_none.return_value = result
    mock.execute = AsyncMock(return_value=execution)
    return mock, cast(AsyncSession, mock)


@pytest.mark.anyio
async def test_resolver_uses_current_verified_address_and_safe_public_sender_name() -> None:
    mock, session = _session(("new-address@example.com", "  <b>Alice</b>\nBuddy  "))

    delivery = await MatchingInvitationCreatedResolver().resolve(
        session,
        aggregate_id=INVITATION_ID,
        recipient_user_id=RECIPIENT_ID,
        payload={"invitation_id": str(INVITATION_ID)},
    )

    assert delivery.recipient_email == "new-address@example.com"
    assert delivery.payload == {
        "version": 1,
        "invitation_id": str(INVITATION_ID),
        "sender_display_name": "<b>Alice</b> Buddy",
    }
    assert "new-address@example.com" not in repr(delivery)
    mock.execute.assert_awaited_once()


@pytest.mark.anyio
async def test_resolver_suppresses_unverified_inactive_deleted_or_missing_recipient() -> None:
    _mock, session = _session(None)

    with pytest.raises(EmailTemplateError) as raised:
        await MatchingInvitationCreatedResolver().resolve(
            session,
            aggregate_id=INVITATION_ID,
            recipient_user_id=RECIPIENT_ID,
            payload={"invitation_id": str(INVITATION_ID)},
        )

    assert raised.value.error_code == "invitation_recipient_unavailable"
    assert str(raised.value) == "Transactional email template is unavailable."


@pytest.mark.anyio
@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"invitation_id": "not-a-uuid"},
        {"invitation_id": str(INVITATION_ID), "message": "private"},
    ],
)
async def test_resolver_rejects_malformed_or_expanded_persisted_payload(
    payload: dict[str, object],
) -> None:
    mock, session = _session(("recipient@example.com", "Sender"))

    with pytest.raises(EmailTemplateError) as raised:
        await MatchingInvitationCreatedResolver().resolve(
            session,
            aggregate_id=INVITATION_ID,
            recipient_user_id=RECIPIENT_ID,
            payload=payload,
        )

    assert raised.value.error_code == "invitation_payload_invalid"
    mock.execute.assert_not_awaited()


def test_template_renders_focused_plain_text_content_and_same_origin_cta() -> None:
    content = MatchingInvitationCreatedTemplate(SETTINGS).render(
        {
            "version": 1,
            "invitation_id": str(INVITATION_ID),
            "sender_display_name": "<script>alert(1)</script>",
        }
    )

    assert content.subject == "You received a VGU Buddy invitation"
    assert content.text_body.startswith(
        "<script>alert(1)</script> sent you a VGU Buddy invitation."
    )
    assert (
        f"https://staging.vgubuddyprogram.com/user/matching?invitation={INVITATION_ID}"
        in content.text_body
    )
    assert "Start Chatting" not in content.text_body
    assert "message" not in content.text_body.lower()
    assert "example.com" not in content.text_body
    assert str(INVITATION_ID) not in content.subject
    assert "<script>alert(1)</script>" not in repr(content)


@pytest.mark.parametrize(
    "payload",
    [
        {"version": 1, "invitation_id": "invalid", "sender_display_name": "Sender"},
        {
            "version": 1,
            "invitation_id": str(INVITATION_ID),
            "sender_display_name": "Sender\r\nBcc: victim@example.com",
        },
        {
            "version": 2,
            "invitation_id": str(INVITATION_ID),
            "sender_display_name": "Sender",
        },
    ],
)
def test_template_rejects_malformed_resolved_payload(payload: dict[str, object]) -> None:
    with pytest.raises(EmailTemplateError) as raised:
        MatchingInvitationCreatedTemplate(SETTINGS).render(payload)
    assert raised.value.error_code == "invitation_payload_invalid"


@pytest.mark.anyio
async def test_default_registries_allowlist_invitation_without_accepted_email() -> None:
    templates = default_email_template_registry(SETTINGS)
    resolvers = default_email_delivery_resolver_registry()
    _mock, session = _session(("current@example.com", "Sender"))

    content = templates.render(
        MATCHING_INVITATION_CREATED,
        {
            "version": 1,
            "invitation_id": str(INVITATION_ID),
            "sender_display_name": "Sender",
        },
    )
    assert content.subject == "You received a VGU Buddy invitation"
    delivery = await resolvers.resolve(
        session,
        event_type=MATCHING_INVITATION_CREATED,
        aggregate_id=INVITATION_ID,
        recipient_user_id=RECIPIENT_ID,
        recipient_email="creation-snapshot@example.com",
        payload={"invitation_id": str(INVITATION_ID)},
    )
    assert delivery.recipient_email == "current@example.com"
    with pytest.raises(EmailTemplateError) as raised:
        templates.render("MATCHING_INVITATION_ACCEPTED", {})
    assert raised.value.error_code == "template_unregistered"


def test_template_contract_is_time_independent_and_contains_no_expiry_guess() -> None:
    content = MatchingInvitationCreatedTemplate(SETTINGS).render(
        {
            "version": 1,
            "invitation_id": str(INVITATION_ID),
            "sender_display_name": "Sender",
        }
    )
    assert str(datetime(2026, 10, 8, tzinfo=UTC).date()) not in content.text_body
    assert "7 days" not in content.text_body
