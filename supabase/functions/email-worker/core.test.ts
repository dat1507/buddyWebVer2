import assert from "node:assert/strict";
import { test } from "node:test";

import {
  buildWorkerLogEvent,
  DeliveryFailure,
  encodeBase64Url,
  type EmailProvider,
  type FinalizeOutcome,
  type OutboundEmail,
  type OutboxGateway,
  type OutboxJob,
  ResendEmailProvider,
  runEmailWorker,
  type TemplateSettings,
} from "./core.ts";

test("structured worker log contains counts but no sensitive delivery fields", () => {
  const event = buildWorkerLogEvent({
    invocationId: "00000000-0000-4000-8000-000000000000",
    statusCode: 200,
    durationMs: 12.6,
    outcome: "completed_with_retry",
    report: {
      claimed: 2,
      sent: 1,
      retry_scheduled: 1,
      terminal_failed: 0,
      skipped: 0,
    },
    timestamp: "2026-09-26T00:00:00.000Z",
  });

  assert.deepEqual(event, {
    timestamp: "2026-09-26T00:00:00.000Z",
    level: "warning",
    service: "vgu-buddy-email-worker",
    event: "email_worker_invocation_completed",
    invocation_id: "00000000-0000-4000-8000-000000000000",
    status_code: 200,
    duration_ms: 13,
    outcome: "completed_with_retry",
    claimed: 2,
    sent: 1,
    retry_scheduled: 1,
    terminal_failed: 0,
    skipped: 0,
  });
  assert.equal("recipient_email" in event, false);
  assert.equal("payload" in event, false);
  assert.equal("idempotency_key" in event, false);
  assert.equal("provider_message_id" in event, false);
});

const NOW = new Date("2026-09-25T00:00:00.000Z");
const SEALING_KEY = Uint8Array.from({ length: 32 }, (_, index) => index + 1);
const TEMPLATE_SETTINGS: TemplateSettings = {
  publicAppBaseUrl: "https://staging.vgubuddyprogram.com",
  sealingKey: SEALING_KEY,
};

interface StoredJob {
  job: OutboxJob;
  leaseOwner: string | null;
  attempts: number;
  sent: boolean;
  failed: boolean;
}

class AtomicFakeGateway implements OutboxGateway {
  readonly stored: StoredJob[];
  readonly claims: number[] = [];

  constructor(jobs: readonly OutboxJob[]) {
    this.stored = jobs.map((job) => ({
      job,
      leaseOwner: null,
      attempts: 0,
      sent: false,
      failed: false,
    }));
  }

  async claim(workerId: string, batchSize: number): Promise<readonly OutboxJob[]> {
    this.claims.push(batchSize);
    const selected = this.stored
      .filter((stored) => !stored.sent && !stored.failed && stored.leaseOwner === null)
      .slice(0, batchSize);
    for (const stored of selected) {
      stored.leaseOwner = workerId;
    }
    return selected.map((stored) => stored.job);
  }

  async complete(
    jobId: string,
    workerId: string,
    _providerMessageId: string,
  ): Promise<FinalizeOutcome> {
    const stored = this.stored.find((candidate) => candidate.job.id === jobId);
    if (!stored || stored.sent || stored.failed || stored.leaseOwner !== workerId) {
      return "skipped";
    }
    stored.attempts += 1;
    stored.sent = true;
    stored.leaseOwner = null;
    return "sent";
  }

  async fail(
    jobId: string,
    workerId: string,
    retryable: boolean,
    _errorCode: string,
  ): Promise<FinalizeOutcome> {
    const stored = this.stored.find((candidate) => candidate.job.id === jobId);
    if (!stored || stored.sent || stored.failed || stored.leaseOwner !== workerId) {
      return "skipped";
    }
    stored.attempts += 1;
    stored.leaseOwner = null;
    if (retryable && stored.attempts < 5) {
      return "retry";
    }
    stored.failed = true;
    return "failed";
  }
}

class RecordingProvider implements EmailProvider {
  readonly deliveries: Array<{ message: OutboundEmail; idempotencyKey: string }> = [];
  readonly outcomes: Array<string | DeliveryFailure>;

  constructor(outcomes: Array<string | DeliveryFailure> = []) {
    this.outcomes = [...outcomes];
  }

  async send(message: OutboundEmail, idempotencyKey: string): Promise<string> {
    this.deliveries.push({ message, idempotencyKey });
    const outcome = this.outcomes.shift() ?? `provider-${this.deliveries.length}`;
    if (outcome instanceof DeliveryFailure) {
      throw outcome;
    }
    return outcome;
  }
}

test("A. empty queue returns an empty report without calling the provider", async () => {
  const gateway = new AtomicFakeGateway([]);
  const provider = new RecordingProvider();

  const report = await runEmailWorker(gateway, provider, TEMPLATE_SETTINGS, {
    workerId: "edge-empty",
    now: NOW,
  });

  assert.deepEqual(report, {
    claimed: 0,
    sent: 0,
    retry_scheduled: 0,
    terminal_failed: 0,
    skipped: 0,
  });
  assert.equal(provider.deliveries.length, 0);
});

test("B. normal verification email decrypts the existing payload contract and sends", async () => {
  const job = await verificationJob("normal");
  const gateway = new AtomicFakeGateway([job]);
  const provider = new RecordingProvider(["provider-normal"]);

  const report = await runEmailWorker(gateway, provider, TEMPLATE_SETTINGS, {
    workerId: "edge-normal",
    now: NOW,
  });

  assert.equal(report.sent, 1);
  assert.equal(provider.deliveries.length, 1);
  const delivery = provider.deliveries[0];
  assert.equal(delivery.idempotencyKey, job.idempotency_key);
  assert.equal(delivery.message.subject, "Verify your VGU Buddy email");
  assert.match(
    delivery.message.textBody,
    /^Verify your email address for VGU Buddy by opening this link:/,
  );
  assert.match(delivery.message.textBody, /https:\/\/staging\.vgubuddyprogram\.com\/verify-email/);
  assert.equal(gateway.stored[0].attempts, 1);
  assert.equal(gateway.stored[0].sent, true);
});

test("C. completed work is not claimed twice and Resend receives the stable idempotency key", async () => {
  const job = await verificationJob("idempotent");
  const gateway = new AtomicFakeGateway([job]);
  const provider = new RecordingProvider();

  const first = await runEmailWorker(gateway, provider, TEMPLATE_SETTINGS, {
    workerId: "edge-idempotent-one",
    now: NOW,
  });
  const second = await runEmailWorker(gateway, provider, TEMPLATE_SETTINGS, {
    workerId: "edge-idempotent-two",
    now: NOW,
  });

  assert.equal(first.sent, 1);
  assert.equal(second.claimed, 0);
  assert.deepEqual(
    provider.deliveries.map((delivery) => delivery.idempotencyKey),
    [job.idempotency_key],
  );

  let capturedHeader = "";
  const resend = new ResendEmailProvider(
    "test-only-provider-key",
    "VGU Buddy <mail@example.invalid>",
    async (_input, init) => {
      capturedHeader = new Headers(init?.headers).get("Idempotency-Key") ?? "";
      return Response.json({ id: "provider-idempotent" });
    },
  );
  await resend.send(provider.deliveries[0].message, job.idempotency_key);
  assert.equal(capturedHeader, job.idempotency_key);
});

test("D. retryable provider failure releases the job and a later execution succeeds", async () => {
  const job = await verificationJob("retry");
  const gateway = new AtomicFakeGateway([job]);
  const provider = new RecordingProvider([
    new DeliveryFailure(true, "provider_http_503"),
    "provider-recovered",
  ]);

  const first = await runEmailWorker(gateway, provider, TEMPLATE_SETTINGS, {
    workerId: "edge-retry-one",
    now: NOW,
  });
  const second = await runEmailWorker(gateway, provider, TEMPLATE_SETTINGS, {
    workerId: "edge-retry-two",
    now: NOW,
  });

  assert.equal(first.retry_scheduled, 1);
  assert.equal(second.sent, 1);
  assert.deepEqual(
    provider.deliveries.map((delivery) => delivery.idempotencyKey),
    [job.idempotency_key, job.idempotency_key],
  );
  assert.equal(gateway.stored[0].attempts, 2);
});

test("E. overlapping executions atomically lease one job to only one worker", async () => {
  const job = await verificationJob("concurrent");
  const gateway = new AtomicFakeGateway([job]);
  const provider = new RecordingProvider();

  const reports = await Promise.all([
    runEmailWorker(gateway, provider, TEMPLATE_SETTINGS, {
      workerId: "edge-overlap-one",
      now: NOW,
    }),
    runEmailWorker(gateway, provider, TEMPLATE_SETTINGS, {
      workerId: "edge-overlap-two",
      now: NOW,
    }),
  ]);

  assert.equal(reports.reduce((total, report) => total + report.claimed, 0), 1);
  assert.equal(reports.reduce((total, report) => total + report.sent, 0), 1);
  assert.deepEqual(
    provider.deliveries.map((delivery) => delivery.idempotencyKey),
    [job.idempotency_key],
  );
});

test("F. one invocation cannot claim more than the default bounded batch", async () => {
  const jobs = await Promise.all(
    Array.from({ length: 25 }, (_, index) => verificationJob(`bounded-${index}`)),
  );
  const gateway = new AtomicFakeGateway(jobs);
  const provider = new RecordingProvider();

  const report = await runEmailWorker(gateway, provider, TEMPLATE_SETTINGS, {
    workerId: "edge-bounded",
    now: NOW,
  });

  assert.equal(report.claimed, 20);
  assert.equal(report.sent, 20);
  assert.deepEqual(gateway.claims, [20]);
  assert.equal(gateway.stored.filter((stored) => !stored.sent).length, 5);
});

async function verificationJob(suffix: string): Promise<OutboxJob> {
  const tokenBytes = Uint8Array.from({ length: 32 }, (_, index) => (index + suffix.length) % 256);
  const token = encodeBase64Url(tokenBytes);
  const nonce = Uint8Array.from({ length: 12 }, (_, index) => index + suffix.length);
  const key = await crypto.subtle.importKey("raw", SEALING_KEY, { name: "AES-GCM" }, false, [
    "encrypt",
  ]);
  const sealed = await crypto.subtle.encrypt(
    {
      name: "AES-GCM",
      iv: nonce,
      additionalData: new TextEncoder().encode("vgu-buddy-email-verification-delivery-v1"),
    },
    key,
    new TextEncoder().encode(token),
  );
  return {
    id: crypto.randomUUID(),
    event_type: "EMAIL_VERIFICATION_REQUESTED",
    recipient_email: "recipient@example.invalid",
    idempotency_key: `EMAIL_VERIFICATION_REQUESTED/${suffix}`,
    payload: {
      version: 1,
      nonce: encodeBase64Url(nonce),
      sealed_value: encodeBase64Url(new Uint8Array(sealed)),
      expires_at: "2026-09-25T00:15:00+00:00",
    },
  };
}
