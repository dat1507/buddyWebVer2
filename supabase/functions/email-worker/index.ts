import postgres from "npm:postgres@3.4.7";

import {
  buildWorkerLogEvent,
  constantTimeSecretEquals,
  decodeSealingKey,
  DEFAULT_BATCH_SIZE,
  type FinalizeOutcome,
  type OutboxGateway,
  type OutboxJob,
  ResendEmailProvider,
  runEmailWorker,
  type WorkerOutcome,
  type WorkerReport,
} from "./core.ts";

const REQUIRED_ENVIRONMENT = [
  "OUTBOX_DATABASE_URL",
  "RESEND_API_KEY",
  "EMAIL_FROM_ADDRESS",
  "PUBLIC_APP_BASE_URL",
  "EMAIL_VERIFICATION_SEALING_KEY",
  "EMAIL_WORKER_CRON_SECRET",
] as const;

Deno.serve(async (request: Request): Promise<Response> => {
  const invocationId = crypto.randomUUID();
  const startedAt = performance.now();
  let statusCode = 503;
  let outcome: WorkerOutcome = "worker_unavailable";
  let report: WorkerReport | undefined;
  let sql: ReturnType<typeof postgres> | undefined;

  try {
    if (request.method !== "POST") {
      statusCode = 405;
      outcome = "method_not_allowed";
      return jsonResponse({ error: outcome }, statusCode, { Allow: "POST" });
    }

    let environment: Record<(typeof REQUIRED_ENVIRONMENT)[number], string>;
    try {
      environment = readEnvironment();
    } catch {
      statusCode = 503;
      outcome = "configuration_unavailable";
      return jsonResponse({ error: "worker_configuration_unavailable" }, statusCode);
    }

    const suppliedSecret = request.headers.get("x-cron-secret") ?? "";
    if (!(await constantTimeSecretEquals(suppliedSecret, environment.EMAIL_WORKER_CRON_SECRET))) {
      statusCode = 401;
      outcome = "unauthorized";
      return jsonResponse({ error: outcome }, statusCode);
    }

    sql = postgres(environment.OUTBOX_DATABASE_URL, {
      max: 1,
      prepare: false,
      connect_timeout: 10,
      idle_timeout: 5,
    });
    const database = sql;
    const gateway: OutboxGateway = {
      async claim(workerId: string, batchSize: number): Promise<readonly OutboxJob[]> {
        const rows = await database`
        SELECT id, event_type, recipient_email, idempotency_key, payload
        FROM app_private.claim_transactional_email_outbox(${workerId}, ${batchSize})
      `;
        return rows as unknown as OutboxJob[];
      },
      async complete(
        jobId: string,
        workerId: string,
        providerMessageId: string,
      ): Promise<FinalizeOutcome> {
        const rows = await database`
        SELECT app_private.complete_transactional_email_outbox(
          ${jobId}::uuid,
          ${workerId},
          ${providerMessageId}
        ) AS outcome
      `;
        return readOutcome(rows[0]?.outcome);
      },
      async fail(
        jobId: string,
        workerId: string,
        retryable: boolean,
        errorCode: string,
      ): Promise<FinalizeOutcome> {
        const rows = await database`
        SELECT app_private.fail_transactional_email_outbox(
          ${jobId}::uuid,
          ${workerId},
          ${retryable},
          ${errorCode}
        ) AS outcome
      `;
        return readOutcome(rows[0]?.outcome);
      },
    };

    const provider = new ResendEmailProvider(
      environment.RESEND_API_KEY,
      environment.EMAIL_FROM_ADDRESS,
    );
    report = await runEmailWorker(
      gateway,
      provider,
      {
        publicAppBaseUrl: environment.PUBLIC_APP_BASE_URL,
        sealingKey: decodeSealingKey(environment.EMAIL_VERIFICATION_SEALING_KEY),
      },
      { batchSize: DEFAULT_BATCH_SIZE },
    );
    statusCode = 200;
    outcome = report.terminal_failed > 0
      ? "completed_with_terminal_failure"
      : report.retry_scheduled > 0
        ? "completed_with_retry"
        : "completed";
    return jsonResponse(report, statusCode);
  } catch {
    statusCode = 503;
    outcome = "worker_unavailable";
    return jsonResponse({ error: outcome }, statusCode);
  } finally {
    if (sql !== undefined) {
      try {
        await sql.end({ timeout: 1 });
      } catch {
        // The invocation result is already determined; never reflect connection diagnostics.
      }
    }
    console.info(
      JSON.stringify(
        buildWorkerLogEvent({
          invocationId,
          statusCode,
          durationMs: performance.now() - startedAt,
          outcome,
          report,
        }),
      ),
    );
  }
});

function readEnvironment(): Record<(typeof REQUIRED_ENVIRONMENT)[number], string> {
  return Object.fromEntries(
    REQUIRED_ENVIRONMENT.map((name) => {
      const value = Deno.env.get(name);
      if (value === undefined || !value.trim()) {
        throw new Error("Missing Edge Function configuration.");
      }
      return [name, value];
    }),
  ) as Record<(typeof REQUIRED_ENVIRONMENT)[number], string>;
}

function readOutcome(value: unknown): FinalizeOutcome {
  if (value === "sent" || value === "retry" || value === "failed" || value === "skipped") {
    return value;
  }
  throw new Error("Invalid outbox state-transition response.");
}

function jsonResponse(
  body: Record<string, unknown>,
  status: number,
  additionalHeaders: Record<string, string> = {},
): Response {
  return Response.json(body, {
    status,
    headers: {
      "Cache-Control": "no-store",
      ...additionalHeaders,
    },
  });
}
