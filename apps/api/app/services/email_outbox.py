"""Transactional email enqueue, template registry, leases, and bounded delivery retries."""

from __future__ import annotations

import json
import re
from collections.abc import Callable, Collection, Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Final, Protocol
from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models import TransactionalOutbox
from app.services.auth import EmailValidationError, canonicalize_email
from app.services.email_provider import EmailDeliveryError, EmailProvider, OutboundEmail

if TYPE_CHECKING:
    from app.core.config import EmailVerificationDeliverySettings

OUTBOX_LEASE_TTL: Final = timedelta(minutes=5)
MAX_DELIVERY_ATTEMPTS: Final = 5
MAX_OUTBOX_BATCH_SIZE: Final = 100
DEFAULT_OUTBOX_BATCH_SIZE: Final = 20
_MAX_RETRY_DELAY: Final = timedelta(hours=1)
_EVENT_TYPE = re.compile(r"^[A-Z][A-Z0-9_]{0,99}$")
_SENSITIVE_PAYLOAD_KEY: Final = re.compile(
    r"(?:token|secret|password|authorization|credential|api[_-]?key)",
    re.IGNORECASE,
)

Clock = Callable[[], datetime]


class OutboxValidationError(ValueError):
    """Raised when trusted application code supplies an unsafe outbox event."""


class EmailTemplateError(ValueError):
    """Sanitized failure from the server-owned email template boundary."""

    def __init__(self, error_code: str) -> None:
        super().__init__("Transactional email template is unavailable.")
        self.error_code = error_code


@dataclass(frozen=True, slots=True)
class RenderedEmailContent:
    """Template output excluded from representations and persistence."""

    subject: str = field(repr=False)
    text_body: str = field(repr=False)


class EmailTemplateRenderer(Protocol):
    event_type: str

    def render(self, payload: Mapping[str, object]) -> RenderedEmailContent: ...


class EmailTemplateRegistry:
    """Explicit renderer allowlist; persisted event types never select arbitrary templates."""

    def __init__(self, renderers: Collection[EmailTemplateRenderer]) -> None:
        registered: dict[str, EmailTemplateRenderer] = {}
        for renderer in renderers:
            if _EVENT_TYPE.fullmatch(renderer.event_type) is None:
                raise ValueError("Email template event type is invalid.")
            if renderer.event_type in registered:
                raise ValueError("Email template event types must be unique.")
            registered[renderer.event_type] = renderer
        self._renderers = registered

    def render(
        self,
        event_type: str,
        payload: Mapping[str, object],
    ) -> RenderedEmailContent:
        renderer = self._renderers.get(event_type)
        if renderer is None:
            raise EmailTemplateError("template_unregistered")
        try:
            content = renderer.render(payload)
            OutboundEmail(
                recipient_email="validation@example.invalid",
                subject=content.subject,
                text_body=content.text_body,
            )
            return content
        except EmailTemplateError:
            raise
        except Exception:
            raise EmailTemplateError("template_render_failed") from None


@dataclass(frozen=True, slots=True)
class OutboxWorkerReport:
    claimed: int
    sent: int
    retry_scheduled: int
    terminal_failed: int
    skipped: int


@dataclass(frozen=True, slots=True)
class _EmailWorkItem:
    outbox_id: UUID
    event_type: str
    recipient_email: str = field(repr=False)
    idempotency_key: str = field(repr=False)
    payload: dict[str, object] = field(repr=False)


def _system_utc_now() -> datetime:
    return datetime.now(UTC)


def _utc_now(clock: Clock) -> datetime:
    value = clock()
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("Outbox timestamps must be timezone-aware.")
    return value.astimezone(UTC)


def _contains_sensitive_key(value: object) -> bool:
    if isinstance(value, Mapping):
        for key, nested in value.items():
            if not isinstance(key, str) or _SENSITIVE_PAYLOAD_KEY.search(key) is not None:
                return True
            if _contains_sensitive_key(nested):
                return True
    elif isinstance(value, list | tuple):
        return any(_contains_sensitive_key(item) for item in value)
    return False


def _validated_payload(payload: Mapping[str, object]) -> dict[str, object]:
    normalized = dict(payload)
    if _contains_sensitive_key(normalized):
        raise OutboxValidationError("Outbox payload contains a forbidden sensitive field.")
    try:
        json.dumps(normalized, ensure_ascii=False, allow_nan=False)
    except (TypeError, ValueError):
        raise OutboxValidationError("Outbox payload must be a JSON-safe object.") from None
    return normalized


def _validate_identifier(value: str, *, name: str, maximum: int) -> str:
    normalized = value.strip()
    if not normalized or len(normalized) > maximum or "\r" in normalized or "\n" in normalized:
        raise OutboxValidationError(f"Outbox {name} is unsafe or invalid.")
    return normalized


async def enqueue_transactional_email(
    session: AsyncSession,
    *,
    event_type: str,
    aggregate_id: UUID,
    recipient_user_id: UUID | None,
    recipient_email: str,
    idempotency_key: str,
    payload: Mapping[str, object],
    clock: Clock = _system_utc_now,
) -> TransactionalOutbox:
    """Stage an outbox row inside the caller's business transaction without sending email."""
    normalized_event_type = _validate_identifier(event_type, name="event type", maximum=100)
    if _EVENT_TYPE.fullmatch(normalized_event_type) is None:
        raise OutboxValidationError("Outbox event type is unsafe or invalid.")
    normalized_key = _validate_identifier(
        idempotency_key,
        name="idempotency key",
        maximum=256,
    )
    try:
        normalized_email = canonicalize_email(recipient_email)
    except EmailValidationError:
        raise OutboxValidationError("Outbox recipient email is invalid.") from None
    current_time = _utc_now(clock)
    outbox = TransactionalOutbox(
        event_type=normalized_event_type,
        aggregate_id=aggregate_id,
        recipient_user_id=recipient_user_id,
        recipient_email=normalized_email,
        idempotency_key=normalized_key,
        payload=_validated_payload(payload),
        attempts=0,
        next_attempt_at=current_time,
        created_at=current_time,
        updated_at=current_time,
    )
    session.add(outbox)
    await session.flush()
    return outbox


async def claim_transactional_outbox(
    session: AsyncSession,
    *,
    worker_id: str,
    batch_size: int = DEFAULT_OUTBOX_BATCH_SIZE,
    clock: Clock = _system_utc_now,
) -> tuple[UUID, ...]:
    """Lease one ready SKIP LOCKED batch; caller commits before external delivery."""
    normalized_worker_id = _validate_identifier(worker_id, name="worker ID", maximum=100)
    if not 1 <= batch_size <= MAX_OUTBOX_BATCH_SIZE:
        raise OutboxValidationError("Outbox batch size is outside the supported range.")
    current_time = _utc_now(clock)
    statement = (
        select(TransactionalOutbox)
        .where(
            TransactionalOutbox.deleted_at.is_(None),
            TransactionalOutbox.sent_at.is_(None),
            TransactionalOutbox.failed_at.is_(None),
            TransactionalOutbox.next_attempt_at <= current_time,
            or_(
                TransactionalOutbox.lease_expires_at.is_(None),
                TransactionalOutbox.lease_expires_at <= current_time,
            ),
        )
        .order_by(TransactionalOutbox.next_attempt_at, TransactionalOutbox.id)
        .limit(batch_size)
        .with_for_update(skip_locked=True)
    )
    claimed = tuple((await session.scalars(statement)).all())
    lease_expires_at = current_time + OUTBOX_LEASE_TTL
    for row in claimed:
        row.lease_owner = normalized_worker_id
        row.lease_expires_at = lease_expires_at
        row.updated_at = current_time
    if claimed:
        await session.flush()
    return tuple(row.id for row in claimed)


async def _load_work_item(
    factory: async_sessionmaker[AsyncSession],
    outbox_id: UUID,
    worker_id: str,
    clock: Clock,
) -> _EmailWorkItem | None:
    async with factory() as session:
        row = await session.scalar(
            select(TransactionalOutbox).where(TransactionalOutbox.id == outbox_id)
        )
        current_time = _utc_now(clock)
        if (
            row is None
            or row.deleted_at is not None
            or row.sent_at is not None
            or row.failed_at is not None
            or row.lease_owner != worker_id
            or row.lease_expires_at is None
            or row.lease_expires_at <= current_time
        ):
            return None
        return _EmailWorkItem(
            outbox_id=row.id,
            event_type=row.event_type,
            recipient_email=row.recipient_email,
            idempotency_key=row.idempotency_key,
            payload=dict(row.payload),
        )


def _retry_delay(attempts: int) -> timedelta:
    delay = timedelta(minutes=2 ** max(attempts - 1, 0))
    return min(delay, _MAX_RETRY_DELAY)


async def _finalize_delivery(
    factory: async_sessionmaker[AsyncSession],
    *,
    outbox_id: UUID,
    worker_id: str,
    provider_message_id: str | None,
    failure: EmailDeliveryError | EmailTemplateError | None,
    clock: Clock,
) -> str:
    async with factory() as session:
        row = await session.scalar(
            select(TransactionalOutbox)
            .where(TransactionalOutbox.id == outbox_id)
            .with_for_update()
        )
        if (
            row is None
            or row.deleted_at is not None
            or row.sent_at is not None
            or row.failed_at is not None
            or row.lease_owner != worker_id
        ):
            await session.rollback()
            return "skipped"

        current_time = _utc_now(clock)
        row.attempts += 1
        row.lease_owner = None
        row.lease_expires_at = None
        row.updated_at = current_time
        if failure is None:
            if provider_message_id is None:
                raise RuntimeError("Successful email delivery requires a provider message ID.")
            row.sent_at = current_time
            row.provider_message_id = provider_message_id
            row.last_error_code = None
            outcome = "sent"
        else:
            row.last_error_code = failure.error_code
            retryable = isinstance(failure, EmailDeliveryError) and failure.retryable
            if retryable and row.attempts < MAX_DELIVERY_ATTEMPTS:
                row.next_attempt_at = current_time + _retry_delay(row.attempts)
                outcome = "retry"
            else:
                row.failed_at = current_time
                outcome = "failed"
        await session.commit()
        return outcome


async def _deliver_one(
    factory: async_sessionmaker[AsyncSession],
    *,
    outbox_id: UUID,
    worker_id: str,
    provider: EmailProvider,
    templates: EmailTemplateRegistry,
    clock: Clock,
) -> str:
    item = await _load_work_item(factory, outbox_id, worker_id, clock)
    if item is None:
        return "skipped"
    try:
        content = templates.render(item.event_type, item.payload)
        delivery = await provider.send(
            OutboundEmail(
                recipient_email=item.recipient_email,
                subject=content.subject,
                text_body=content.text_body,
            ),
            idempotency_key=item.idempotency_key,
        )
        provider_message_id = delivery.provider_message_id
        failure: EmailDeliveryError | EmailTemplateError | None = None
    except EmailDeliveryError as error:
        provider_message_id = None
        failure = error
    except EmailTemplateError as error:
        provider_message_id = None
        failure = error
    return await _finalize_delivery(
        factory,
        outbox_id=outbox_id,
        worker_id=worker_id,
        provider_message_id=provider_message_id,
        failure=failure,
        clock=clock,
    )


async def process_transactional_outbox_batch(
    factory: async_sessionmaker[AsyncSession],
    *,
    worker_id: str,
    provider: EmailProvider,
    templates: EmailTemplateRegistry,
    batch_size: int = DEFAULT_OUTBOX_BATCH_SIZE,
    clock: Clock = _system_utc_now,
) -> OutboxWorkerReport:
    """Claim, commit, deliver, and finalize one bounded batch outside business transactions."""
    async with factory() as session:
        claimed_ids = await claim_transactional_outbox(
            session,
            worker_id=worker_id,
            batch_size=batch_size,
            clock=clock,
        )
        await session.commit()

    outcomes = [
        await _deliver_one(
            factory,
            outbox_id=outbox_id,
            worker_id=worker_id,
            provider=provider,
            templates=templates,
            clock=clock,
        )
        for outbox_id in claimed_ids
    ]
    return OutboxWorkerReport(
        claimed=len(claimed_ids),
        sent=outcomes.count("sent"),
        retry_scheduled=outcomes.count("retry"),
        terminal_failed=outcomes.count("failed"),
        skipped=outcomes.count("skipped"),
    )


def default_email_template_registry(
    settings: EmailVerificationDeliverySettings,
) -> EmailTemplateRegistry:
    """Return the reviewed built-in transactional-email template allowlist."""
    from app.services.email_verification_requests import EmailVerificationTemplate

    return EmailTemplateRegistry((EmailVerificationTemplate(settings),))
