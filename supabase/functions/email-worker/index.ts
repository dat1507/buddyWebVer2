import postgres from "npm:postgres@3.4.7";

import {
  constantTimeSecretEquals,
  decodeSealingKey,
  DEFAULT_BATCH_SIZE,
  type FinalizeOutcome,
  type OutboxGateway,
  type OutboxJob,
  ResendEmailProvider,
  runEmailWorker,
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
  if (request.method !== "POST") {
    return jsonResponse({ error: "method_not_allowed" }, 405, { Allow: "POST" });
  }

  let environment: Record<(typeof REQUIRED_ENVIRONMENT)[number], string>;
  try {
    environment = readEnvironment();
  } catch {
    return jsonResponse({ error: "worker_configuration_unavailable" }, 503);
  }

  const suppliedSecret = request.headers.get("x-cron-secret") ?? "";
  if (!(await constantTimeSecretEquals(suppliedSecret, environment.EMAIL_WORKER_CRON_SECRET))) {
    return jsonResponse({ error: "unauthorized" }, 401);
  }

  const sql = postgres(environment.OUTBOX_DATABASE_URL, {
    max: 1,
    prepare: false,
    connect_timeout: 10,
    idle_timeout: 5,
  });
  const gateway: OutboxGateway = {
    async claim(workerId: string, batchSize: number): Promise<readonly OutboxJob[]> {
      const rows = await sql`
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
      const rows = await sql`
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
      const rows = await sql`
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

  try {
    const provider = new ResendEmailProvider(
      environment.RESEND_API_KEY,
      environment.EMAIL_FROM_ADDRESS,
    );
    const report = await runEmailWorker(
      gateway,
      provider,
      {
        publicAppBaseUrl: environment.PUBLIC_APP_BASE_URL,
        sealingKey: decodeSealingKey(environment.EMAIL_VERIFICATION_SEALING_KEY),
      },
      { batchSize: DEFAULT_BATCH_SIZE },
    );
    return jsonResponse(report, 200);
  } catch {
    return jsonResponse({ error: "worker_unavailable" }, 503);
  } finally {
    await sql.end({ timeout: 1 });
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
