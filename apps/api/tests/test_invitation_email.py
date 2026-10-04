"""INV-008/009 current-address resolution and email template tests."""

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
from app.services.invitation_acceptance import MATCHING_INVITATION_ACCEPTED
from app.services.invitation_email import (
    MatchingInvitationAcceptedResolver,
    MatchingInvitationAcceptedTemplate,
    MatchingInvitationCreatedResolver,
    MatchingInvitationCreatedTemplate,
)
from app.services.invitation_sending import MATCHING_INVITATION_CREATED

INVITATION_ID = UUID("11111111-1111-4111-8111-111111111111")
RECIPIENT_ID = UUID("22222222-2222-4222-8222-222222222222")
MATCH_ID = UUID("33333333-3333-4333-8333-333333333333")
CONVERSATION_ID = UUID("44444444-4444-4444-8444-444444444444")
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


def test_template_renders_branded_html_plain_text_fallback_and_same_origin_cta() -> None:
    content = MatchingInvitationCreatedTemplate(SETTINGS).render(
        {
            "version": 1,
            "invitation_id": str(INVITATION_ID),
            "sender_display_name": "<script>alert(1)</script>",
        }
    )

    assert content.subject == "You received a VGU Buddy invitation"
    assert content.text_body.startswith("You've got a new Buddy invitation!")
    assert (
        "<script>alert(1)</script> would like to connect with you on VGU Buddy."
        in content.text_body
    )
    assert (
        f"https://staging.vgubuddyprogram.com/user/matching?invitation={INVITATION_ID}"
        in content.text_body
    )
    assert "This invitation will expire after 7 days." in content.text_body
    assert content.html_body is not None
    assert "You've got a new Buddy invitation!" in content.html_body
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in content.html_body
    assert "<script>alert(1)</script>" not in content.html_body
    assert 'src="https://staging.vgubuddyprogram.com/vguBuddy_logo.png"' in content.html_body
    assert (
        f'href="https://staging.vgubuddyprogram.com/user/matching?invitation={INVITATION_ID}"'
        in content.html_body
    )
    assert ">View invitation</a>" in content.html_body
    assert "This invitation will expire after 7 days." in content.html_body
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
async def test_default_registries_keep_created_and_accepted_events_separate() -> None:
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
    accepted = templates.render(
        MATCHING_INVITATION_ACCEPTED,
        {
            "version": 1,
            "conversation_id": str(CONVERSATION_ID),
            "acceptor_display_name": "Buddy",
        },
    )
    assert accepted.subject == "Your VGU Buddy invitation was accepted"
    accepted_delivery = await resolvers.resolve(
        session,
        event_type=MATCHING_INVITATION_ACCEPTED,
        aggregate_id=INVITATION_ID,
        recipient_user_id=RECIPIENT_ID,
        recipient_email="acceptance-snapshot@example.com",
        payload={
            "invitation_id": str(INVITATION_ID),
            "match_id": str(MATCH_ID),
            "conversation_id": str(CONVERSATION_ID),
        },
    )
    assert accepted_delivery.recipient_email == "current@example.com"
    with pytest.raises(EmailTemplateError) as raised:
        templates.render(
            MATCHING_INVITATION_CREATED,
            {
                "version": 1,
                "conversation_id": str(CONVERSATION_ID),
                "acceptor_display_name": "Buddy",
            },
        )
    assert raised.value.error_code == "invitation_payload_invalid"


def test_template_contract_uses_the_business_rule_without_an_absolute_expiry_guess() -> None:
    content = MatchingInvitationCreatedTemplate(SETTINGS).render(
        {
            "version": 1,
            "invitation_id": str(INVITATION_ID),
            "sender_display_name": "Sender",
        }
    )
    assert str(datetime(2026, 10, 8, tzinfo=UTC).date()) not in content.text_body
    assert "This invitation will expire after 7 days." in content.text_body
    assert content.html_body is not None
    assert str(datetime(2026, 10, 8, tzinfo=UTC).date()) not in content.html_body
    assert "This invitation will expire after 7 days." in content.html_body


@pytest.mark.anyio
async def test_accepted_resolver_uses_current_sender_address_and_authoritative_relationship() -> (
    None
):
    mock, session = _session(("current-sender@example.com", "  <b>Buddy</b>\nFriend  "))

    delivery = await MatchingInvitationAcceptedResolver().resolve(
        session,
        aggregate_id=INVITATION_ID,
        recipient_user_id=RECIPIENT_ID,
        payload={
            "invitation_id": str(INVITATION_ID),
            "match_id": str(MATCH_ID),
            "conversation_id": str(CONVERSATION_ID),
        },
    )

    assert delivery.recipient_email == "current-sender@example.com"
    assert delivery.payload == {
        "version": 1,
        "conversation_id": str(CONVERSATION_ID),
        "acceptor_display_name": "<b>Buddy</b> Friend",
    }
    assert "current-sender@example.com" not in repr(delivery)
    statement = str(mock.execute.await_args.args[0])
    assert "matching_invitations" in statement
    assert "matches" in statement
    assert "buddy_conversations" in statement


@pytest.mark.anyio
async def test_accepted_resolver_suppresses_unverified_inactive_deleted_or_foreign_sender() -> None:
    _mock, session = _session(None)

    with pytest.raises(EmailTemplateError) as raised:
        await MatchingInvitationAcceptedResolver().resolve(
            session,
            aggregate_id=INVITATION_ID,
            recipient_user_id=RECIPIENT_ID,
            payload={
                "invitation_id": str(INVITATION_ID),
                "match_id": str(MATCH_ID),
                "conversation_id": str(CONVERSATION_ID),
            },
        )

    assert raised.value.error_code == "accepted_invitation_recipient_unavailable"
    assert str(raised.value) == "Transactional email template is unavailable."


@pytest.mark.anyio
@pytest.mark.parametrize(
    "payload",
    [
        {},
        {
            "invitation_id": str(INVITATION_ID),
            "match_id": str(MATCH_ID),
            "conversation_id": "not-a-uuid",
        },
        {
            "invitation_id": str(INVITATION_ID),
            "match_id": str(MATCH_ID),
            "conversation_id": str(CONVERSATION_ID),
            "message": "private",
        },
    ],
)
async def test_accepted_resolver_rejects_malformed_or_expanded_payload(
    payload: dict[str, object],
) -> None:
    mock, session = _session(("current-sender@example.com", "Buddy"))

    with pytest.raises(EmailTemplateError) as raised:
        await MatchingInvitationAcceptedResolver().resolve(
            session,
            aggregate_id=INVITATION_ID,
            recipient_user_id=RECIPIENT_ID,
            payload=payload,
        )

    assert raised.value.error_code == "accepted_invitation_payload_invalid"
    mock.execute.assert_not_awaited()


def test_accepted_template_renders_plain_text_start_chatting_cta() -> None:
    content = MatchingInvitationAcceptedTemplate(SETTINGS).render(
        {
            "version": 1,
            "conversation_id": str(CONVERSATION_ID),
            "acceptor_display_name": "<script>alert(1)</script>",
        }
    )

    assert content.subject == "Your VGU Buddy invitation was accepted"
    assert content.text_body.startswith(
        "<script>alert(1)</script> accepted your VGU Buddy invitation."
    )
    assert (
        f"https://staging.vgubuddyprogram.com/user/buddy?conversation={CONVERSATION_ID}"
        in content.text_body
    )
    assert "Start chatting:" in content.text_body
    assert "message" not in content.text_body.lower()
    assert "example.com" not in content.text_body
    assert str(INVITATION_ID) not in content.text_body
    assert str(MATCH_ID) not in content.text_body
    assert "<script>alert(1)</script>" not in repr(content)


@pytest.mark.parametrize(
    "payload",
    [
        {"version": 1, "conversation_id": "invalid", "acceptor_display_name": "Buddy"},
        {
            "version": 1,
            "conversation_id": str(CONVERSATION_ID),
            "acceptor_display_name": "Buddy\r\nBcc: victim@example.com",
        },
        {
            "version": 2,
            "conversation_id": str(CONVERSATION_ID),
            "acceptor_display_name": "Buddy",
        },
    ],
)
def test_accepted_template_rejects_malformed_resolved_payload(
    payload: dict[str, object],
) -> None:
    with pytest.raises(EmailTemplateError) as raised:
        MatchingInvitationAcceptedTemplate(SETTINGS).render(payload)
    assert raised.value.error_code == "accepted_invitation_payload_invalid"
