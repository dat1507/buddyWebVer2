-- Read-only, redacted snapshot for the scheduled maintenance job.
-- The result contains Cron timing/status only. A successful Cron row proves pg_net enqueue, not
-- remote HTTP 2xx; inspect aggregate API completion events in provider logs.

WITH maintenance_job AS (
    SELECT jobid, active, schedule
    FROM cron.job
    WHERE jobname = 'vgu-buddy-maintenance-every-15-minutes'
),
recent_runs AS (
    SELECT
        max(start_time) AS last_started_at,
        max(end_time) FILTER (WHERE status = 'succeeded') AS last_succeeded_at,
        count(*) FILTER (
            WHERE status <> 'succeeded'
              AND start_time >= now() - interval '1 hour'
        ) AS failed_runs_1h
    FROM cron.job_run_details
    WHERE jobid = (SELECT jobid FROM maintenance_job)
)
SELECT
    now() AS observed_at,
    maintenance_job.active,
    maintenance_job.schedule,
    recent_runs.last_started_at,
    recent_runs.last_succeeded_at,
    recent_runs.failed_runs_1h
FROM maintenance_job
CROSS JOIN recent_runs;
