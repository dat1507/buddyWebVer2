"""Repository-enforceable OPS-003 monitoring and runbook safety contracts."""

from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]


def test_outbox_monitoring_query_is_read_only_and_redacted() -> None:
    sql = (
        REPOSITORY_ROOT / "supabase/monitoring/email-worker-health.sql"
    ).read_text(encoding="utf-8")
    normalized = sql.lower()
    assert "select" in normalized
    assert "ready_count" in normalized
    assert "terminal_failed_count" in normalized
    assert "last_succeeded_at" in normalized
    for mutation in ("insert into", "update ", "delete from", "truncate ", "drop "):
        assert mutation not in normalized

    executable_sql = "\n".join(
        line for line in normalized.splitlines() if not line.lstrip().startswith("--")
    )
    for sensitive_column in (
        "recipient_email",
        "payload",
        "provider_message_id",
        "idempotency_key",
        "lease_owner",
    ):
        assert sensitive_column not in executable_sql


def test_ops003_runbooks_cover_every_required_recovery_gate() -> None:
    documents = [
        REPOSITORY_ROOT / "docs/operations/ops-003-observability.md",
        REPOSITORY_ROOT / "docs/operations/ops-003-recovery.md",
        REPOSITORY_ROOT / "docs/operations/ops-003-credential-rotation.md",
    ]
    combined = "\n".join(path.read_text(encoding="utf-8").lower() for path in documents)
    required_contracts = (
        "api failure",
        "edge function",
        "cron",
        "outbox",
        "redis",
        "wss",
        "backup failure",
        "rollback point",
        "migration recovery decision tree",
        "email outage",
        "credential rotation",
        "signed url",
        "message body",
        "alert routing",
    )
    for contract in required_contracts:
        assert contract in combined


def test_edge_worker_emits_only_fixed_structured_log_builder() -> None:
    core = (
        REPOSITORY_ROOT / "supabase/functions/email-worker/core.ts"
    ).read_text(encoding="utf-8")
    index = (
        REPOSITORY_ROOT / "supabase/functions/email-worker/index.ts"
    ).read_text(encoding="utf-8")
    assert "buildWorkerLogEvent" in core
    assert "email_worker_invocation_completed" in core
    assert "console.info" in index
    assert "buildWorkerLogEvent" in index
