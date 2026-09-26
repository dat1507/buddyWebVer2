-- OPS-003 read-only, redacted operational snapshot.
-- Run with an authorized operator role. The result contains counts/times/error codes only.

WITH outbox AS (
    SELECT
        count(*) FILTER (
            WHERE sent_at IS NULL
              AND failed_at IS NULL
              AND next_attempt_at <= now()
              AND (lease_expires_at IS NULL OR lease_expires_at <= now())
        ) AS ready_count,
        count(*) FILTER (
            WHERE sent_at IS NULL
              AND failed_at IS NULL
              AND lease_expires_at > now()
        ) AS leased_count,
        count(*) FILTER (
            WHERE sent_at IS NULL
              AND failed_at IS NULL
              AND next_attempt_at > now()
        ) AS retry_wait_count,
        count(*) FILTER (WHERE sent_at IS NOT NULL) AS sent_count,
        count(*) FILTER (WHERE failed_at IS NOT NULL) AS terminal_failed_count,
        extract(
            epoch FROM now() - min(created_at) FILTER (
                WHERE sent_at IS NULL
                  AND failed_at IS NULL
                  AND next_attempt_at <= now()
                  AND (lease_expires_at IS NULL OR lease_expires_at <= now())
            )
        )::bigint AS oldest_ready_age_seconds,
        extract(
            epoch FROM now() - min(lease_expires_at) FILTER (
                WHERE sent_at IS NULL
                  AND failed_at IS NULL
                  AND lease_expires_at <= now()
            )
        )::bigint AS oldest_expired_lease_seconds
    FROM app_private.transactional_outbox
),
cron_runs AS (
    SELECT
        max(start_time) AS last_started_at,
        max(end_time) FILTER (WHERE status = 'succeeded') AS last_succeeded_at,
        count(*) FILTER (
            WHERE status <> 'succeeded'
              AND start_time >= now() - interval '15 minutes'
        ) AS failed_runs_15m
    FROM cron.job_run_details
    WHERE jobid = (
        SELECT jobid
        FROM cron.job
        WHERE jobname = 'vgu-buddy-email-worker-every-minute'
    )
)
SELECT
    now() AS observed_at,
    outbox.ready_count,
    outbox.leased_count,
    outbox.retry_wait_count,
    outbox.sent_count,
    outbox.terminal_failed_count,
    outbox.oldest_ready_age_seconds,
    outbox.oldest_expired_lease_seconds,
    cron_runs.last_started_at,
    cron_runs.last_succeeded_at,
    cron_runs.failed_runs_15m
FROM outbox
CROSS JOIN cron_runs;

-- Investigate terminal failure categories without selecting recipient_email, payload,
-- provider_message_id, idempotency_key, lease_owner or any verification material.
SELECT
    coalesce(last_error_code, 'unspecified') AS error_code,
    count(*) AS terminal_failure_count,
    min(failed_at) AS first_failure_at,
    max(failed_at) AS latest_failure_at
FROM app_private.transactional_outbox
WHERE failed_at IS NOT NULL
GROUP BY coalesce(last_error_code, 'unspecified')
ORDER BY terminal_failure_count DESC, error_code;
