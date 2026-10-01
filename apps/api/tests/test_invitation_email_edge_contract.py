"""Offline INV-008 contract checks for the production Edge email path."""

from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]


def _source(path: str) -> str:
    return (REPOSITORY_ROOT / path).read_text(encoding="utf-8")


def test_edge_worker_allowlists_invitation_and_resolves_current_verified_recipient() -> None:
    core = _source("supabase/functions/email-worker/core.ts")
    index = _source("supabase/functions/email-worker/index.ts")

    assert 'const INVITATION_EVENT = "MATCHING_INVITATION_CREATED"' in core
    assert "invitationIdFromCreationPayload(job.payload)" in index
    assert "recipient.email AS recipient_email" in index
    assert "recipient.email_verified_at IS NOT NULL" in index
    assert "recipient.is_active IS TRUE" in index
    assert "recipient.deleted_at IS NULL" in index
    assert "outbox.aggregate_id = ${invitationId}::uuid" in index
    assert "/user/matching?invitation=" in core


def test_invitation_request_path_only_enqueues_and_never_calls_email_provider() -> None:
    sending = _source("apps/api/app/services/invitation_sending.py")

    assert "MATCHING_INVITATION_CREATED" in sending
    assert "enqueue_transactional_email" in sending
    for forbidden in ("ResendEmailProvider", "RESEND_EMAIL_ENDPOINT", "smtplib", "httpx"):
        assert forbidden not in sending


def test_invitation_edge_template_excludes_message_and_accepted_email_behavior() -> None:
    core = _source("supabase/functions/email-worker/core.ts")

    invitation_template = core.split("function renderInvitationEmail", maxsplit=1)[1]
    invitation_template = invitation_template.split(
        "function normalizePublicAppOrigin", maxsplit=1
    )[0]
    assert "invitation message" not in invitation_template.lower()
    assert "MATCHING_INVITATION_ACCEPTED" not in core
    assert "Start Chatting" not in invitation_template
