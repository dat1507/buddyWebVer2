"""Static security contract for the Supabase Cron maintenance caller."""

from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
CRON_SQL = REPOSITORY_ROOT / "supabase" / "cron" / "maintenance-worker.sql"


def test_maintenance_cron_uses_vault_and_one_bounded_https_call() -> None:
    source = CRON_SQL.read_text(encoding="utf-8")

    assert "cron.schedule(" in source
    assert "vgu-buddy-maintenance-every-15-minutes" in source
    assert "*/15 * * * *" in source
    assert "net.http_post(" in source
    assert "timeout_milliseconds := 120000" in source
    assert "vault.decrypted_secrets" in source
    assert "buddy_maintenance_api_url" in source
    assert "buddy_maintenance_cron_secret" in source
    assert "x-cron-secret" in source
    assert "DATABASE_URL" not in source
    assert "SUPABASE_SECRET_KEY" not in source
    assert "staging.vgubuddyprogram.com" not in source
    assert "api.vgubuddyprogram.com" not in source
