-- Run only after the email-worker function is deployed and both named Vault secrets exist.
-- Re-running cron.schedule with this exact case-sensitive name updates the existing job.

DO $$
BEGIN
    IF (
        SELECT count(*)
        FROM vault.decrypted_secrets
        WHERE name IN ('buddy_project_url', 'buddy_email_worker_cron_secret')
    ) <> 2 THEN
        RAISE EXCEPTION 'required email worker Vault configuration is missing';
    END IF;
END
$$;

SELECT cron.schedule(
    'vgu-buddy-email-worker-every-minute',
    '* * * * *',
    $cron$
    SELECT net.http_post(
        url := (
            SELECT decrypted_secret
            FROM vault.decrypted_secrets
            WHERE name = 'buddy_project_url'
        ) || '/functions/v1/email-worker',
        headers := jsonb_build_object(
            'Content-Type', 'application/json',
            'x-cron-secret', (
                SELECT decrypted_secret
                FROM vault.decrypted_secrets
                WHERE name = 'buddy_email_worker_cron_secret'
            )
        ),
        body := jsonb_build_object('scheduled_at', now()),
        timeout_milliseconds := 120000
    ) AS request_id;
    $cron$
);
