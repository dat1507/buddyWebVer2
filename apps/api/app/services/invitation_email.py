"""INV-008 current-address resolver and plain-text invitation email template."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Final
from urllib.parse import quote
from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import EmailVerificationDeliverySettings
from app.models import MatchingInvitation, StudentProfile, User, UserRole
from app.services.email_outbox import (
    EmailTemplateError,
    RenderedEmailContent,
    ResolvedEmailDelivery,
)
from app.services.invitation_sending import MATCHING_INVITATION_CREATED

_RESOLVED_PAYLOAD_VERSION: Final = 1
_FALLBACK_SENDER_NAME: Final = "A VGU Buddy member"


def _safe_sender_display_name(value: str | None) -> str:
    if value is None:
        return _FALLBACK_SENDER_NAME
    normalized = " ".join(value.split())
    return normalized or _FALLBACK_SENDER_NAME


def _invitation_id(payload: Mapping[str, object]) -> UUID:
    if set(payload) != {"invitation_id"} or not isinstance(payload["invitation_id"], str):
        raise EmailTemplateError("invitation_payload_invalid")
    try:
        return UUID(payload["invitation_id"])
    except ValueError:
        raise EmailTemplateError("invitation_payload_invalid") from None


class MatchingInvitationCreatedResolver:
    """Resolve the recipient's current verified address immediately before delivery."""

    event_type = MATCHING_INVITATION_CREATED

    async def resolve(
        self,
        session: AsyncSession,
        *,
        aggregate_id: UUID,
        recipient_user_id: UUID | None,
        payload: Mapping[str, object],
    ) -> ResolvedEmailDelivery:
        if recipient_user_id is None or _invitation_id(payload) != aggregate_id:
            raise EmailTemplateError("invitation_payload_invalid")

        statement = (
            select(User.email, StudentProfile.display_name)
            .select_from(MatchingInvitation)
            .join(
                User,
                and_(
                    User.id == MatchingInvitation.recipient_id,
                    User.id == recipient_user_id,
                    User.role == UserRole.USER,
                    User.is_active.is_(True),
                    User.deleted_at.is_(None),
                    User.email_verified_at.is_not(None),
                ),
            )
            .outerjoin(
                StudentProfile,
                and_(
                    StudentProfile.user_id == MatchingInvitation.sender_id,
                    StudentProfile.deleted_at.is_(None),
                ),
            )
            .where(
                MatchingInvitation.id == aggregate_id,
                MatchingInvitation.recipient_id == recipient_user_id,
                MatchingInvitation.deleted_at.is_(None),
            )
        )
        result = (await session.execute(statement)).one_or_none()
        if result is None:
            raise EmailTemplateError("invitation_recipient_unavailable")
        recipient_email, sender_display_name = result
        return ResolvedEmailDelivery(
            recipient_email=recipient_email,
            payload={
                "version": _RESOLVED_PAYLOAD_VERSION,
                "invitation_id": str(aggregate_id),
                "sender_display_name": _safe_sender_display_name(sender_display_name),
            },
        )


class MatchingInvitationCreatedTemplate:
    """Render the allowlisted Open Invitation notification as plain text only."""

    event_type = MATCHING_INVITATION_CREATED

    def __init__(self, settings: EmailVerificationDeliverySettings) -> None:
        self._public_app_base_url = settings.public_app_base_url

    def render(self, payload: Mapping[str, object]) -> RenderedEmailContent:
        if set(payload) != {"version", "invitation_id", "sender_display_name"}:
            raise EmailTemplateError("invitation_payload_invalid")
        if payload["version"] != _RESOLVED_PAYLOAD_VERSION:
            raise EmailTemplateError("invitation_payload_invalid")
        invitation_id = _invitation_id({"invitation_id": payload["invitation_id"]})
        sender_display_name = payload["sender_display_name"]
        if (
            not isinstance(sender_display_name, str)
            or not sender_display_name
            or len(sender_display_name) > 80
            or "\r" in sender_display_name
            or "\n" in sender_display_name
        ):
            raise EmailTemplateError("invitation_payload_invalid")

        link = (
            f"{self._public_app_base_url}/user/matching"
            f"?invitation={quote(str(invitation_id), safe='')}"
        )
        return RenderedEmailContent(
            subject="You received a VGU Buddy invitation",
            text_body=(
                f"{sender_display_name} sent you a VGU Buddy invitation.\n\n"
                "Open invitation:\n"
                f"{link}\n\n"
                "Sign in to VGU Buddy to review and respond to this invitation."
            ),
        )


__all__ = ["MatchingInvitationCreatedResolver", "MatchingInvitationCreatedTemplate"]
