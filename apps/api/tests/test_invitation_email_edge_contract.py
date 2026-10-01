"""Offline INV-008/009 contract checks for the production Edge email path."""

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


def test_created_and_accepted_edge_templates_are_separate_and_exclude_message() -> None:
    core = _source("supabase/functions/email-worker/core.ts")
    index = _source("supabase/functions/email-worker/index.ts")

    invitation_template = core.split("function renderInvitationEmail", maxsplit=1)[1]
    invitation_template = invitation_template.split(
        "function renderAcceptedInvitationEmail", maxsplit=1
    )[0]
    accepted_template = core.split("function renderAcceptedInvitationEmail", maxsplit=1)[1]
    accepted_template = accepted_template.split("function requireUuid", maxsplit=1)[0]
    assert "invitation message" not in invitation_template.lower()
    assert "Start Chatting" not in invitation_template
    assert 'const ACCEPTED_INVITATION_EVENT = "MATCHING_INVITATION_ACCEPTED"' in core
    assert "acceptedInvitationReferenceFromPayload(job.payload)" in index
    assert "original_sender.email AS recipient_email" in index
    assert "original_sender.email_verified_at IS NOT NULL" in index
    assert "buddy_match.accepted_invitation_id = invitation.id" in index
    assert "conversation.match_id = buddy_match.id" in index
    assert "/user/buddy?conversation=" in accepted_template
    assert "invitation message" not in accepted_template.lower()


def test_acceptance_request_path_only_enqueues_and_never_calls_email_provider() -> None:
    acceptance = _source("apps/api/app/services/invitation_acceptance.py")

    assert "MATCHING_INVITATION_ACCEPTED" in acceptance
    assert "enqueue_transactional_email" in acceptance
    for forbidden in ("ResendEmailProvider", "RESEND_EMAIL_ENDPOINT", "smtplib", "httpx"):
        assert forbidden not in acceptance
