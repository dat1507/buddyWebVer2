-- Run only after the API maintenance endpoint is deployed and both Vault secrets exist.
-- The URL is the full HTTPS endpoint, for example:
-- https://api.example.com/api/internal/maintenance
-- Re-running cron.schedule with this exact case-sensitive name updates the existing job.

DO $$
BEGIN
    IF (
        SELECT count(*)
        FROM vault.decrypted_secrets
        WHERE name IN ('buddy_maintenance_api_url', 'buddy_maintenance_cron_secret')
    ) <> 2 THEN
        RAISE EXCEPTION 'required maintenance worker Vault configuration is missing';
    END IF;
END
$$;

SELECT cron.schedule(
    'vgu-buddy-maintenance-every-15-minutes',
    '*/15 * * * *',
    $cron$
    SELECT net.http_post(
        url := (
            SELECT decrypted_secret
            FROM vault.decrypted_secrets
            WHERE name = 'buddy_maintenance_api_url'
        ),
        headers := jsonb_build_object(
            'Content-Type', 'application/json',
            'x-cron-secret', (
                SELECT decrypted_secret
                FROM vault.decrypted_secrets
                WHERE name = 'buddy_maintenance_cron_secret'
            )
        ),
        body := jsonb_build_object('scheduled_at', now()),
        timeout_milliseconds := 120000
    ) AS request_id;
    $cron$
);
