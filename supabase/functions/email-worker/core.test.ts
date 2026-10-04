import assert from "node:assert/strict";
import { test } from "node:test";

import {
  acceptedInvitationReferenceFromPayload,
  buildWorkerLogEvent,
  DeliveryFailure,
  encodeBase64Url,
  invitationIdFromCreationPayload,
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
  lastErrorCode: string | null;
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
      lastErrorCode: null,
    }));
  }

  async claim(
    workerId: string,
    batchSize: number,
  ): Promise<readonly OutboxJob[]> {
    this.claims.push(batchSize);
    const selected = this.stored
      .filter(
        (stored) =>
          !stored.sent && !stored.failed && stored.leaseOwner === null,
      )
      .slice(0, batchSize);
    for (const stored of selected) {
      stored.leaseOwner = workerId;
    }
    return selected.map((stored) => stored.job);
  }

  async resolve(job: OutboxJob): Promise<OutboxJob> {
    return job;
  }

  async complete(
    jobId: string,
    workerId: string,
    _providerMessageId: string,
  ): Promise<FinalizeOutcome> {
    const stored = this.stored.find((candidate) => candidate.job.id === jobId);
    if (
      !stored ||
      stored.sent ||
      stored.failed ||
      stored.leaseOwner !== workerId
    ) {
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
    errorCode: string,
  ): Promise<FinalizeOutcome> {
    const stored = this.stored.find((candidate) => candidate.job.id === jobId);
    if (
      !stored ||
      stored.sent ||
      stored.failed ||
      stored.leaseOwner !== workerId
    ) {
      return "skipped";
    }
    stored.attempts += 1;
    stored.leaseOwner = null;
    stored.lastErrorCode = errorCode;
    if (retryable && stored.attempts < 5) {
      return "retry";
    }
    stored.failed = true;
    return "failed";
  }
}

class RecordingProvider implements EmailProvider {
  readonly deliveries: Array<{
    message: OutboundEmail;
    idempotencyKey: string;
  }> = [];
  readonly outcomes: Array<string | DeliveryFailure>;

  constructor(outcomes: Array<string | DeliveryFailure> = []) {
    this.outcomes = [...outcomes];
  }

  async send(message: OutboundEmail, idempotencyKey: string): Promise<string> {
    this.deliveries.push({ message, idempotencyKey });
    const outcome =
      this.outcomes.shift() ?? `provider-${this.deliveries.length}`;
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
  assert.match(
    delivery.message.textBody,
    /https:\/\/staging\.vgubuddyprogram\.com\/verify-email/,
  );
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

test("Resend sends HTML with a plain-text fallback when a template provides both", async () => {
  let capturedBody: unknown;
  const resend = new ResendEmailProvider(
    "test-only-provider-key",
    "VGU Buddy <mail@example.invalid>",
    async (_input, init) => {
      capturedBody = JSON.parse(String(init?.body));
      return Response.json({ id: "provider-html" });
    },
  );

  await resend.send(
    {
      recipientEmail: "student@example.invalid",
      subject: "Subject",
      textBody: "Plain-text fallback",
      htmlBody: "<strong>HTML body</strong>",
    },
    "email-with-html",
  );

  assert.deepEqual(capturedBody, {
    from: "VGU Buddy <mail@example.invalid>",
    to: ["student@example.invalid"],
    subject: "Subject",
    text: "Plain-text fallback",
    html: "<strong>HTML body</strong>",
  });
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

  assert.equal(
    reports.reduce((total, report) => total + report.claimed, 0),
    1,
  );
  assert.equal(
    reports.reduce((total, report) => total + report.sent, 0),
    1,
  );
  assert.deepEqual(
    provider.deliveries.map((delivery) => delivery.idempotencyKey),
    [job.idempotency_key],
  );
});

test("F. one invocation cannot claim more than the default bounded batch", async () => {
  const jobs = await Promise.all(
    Array.from({ length: 25 }, (_, index) =>
      verificationJob(`bounded-${index}`),
    ),
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

test("INV-008 resolves current address and renders one branded invitation email", async () => {
  const job = invitationJob("invite-current");
  class InvitationGateway extends AtomicFakeGateway {
    override async resolve(claimed: OutboxJob): Promise<OutboxJob> {
      return {
        ...claimed,
        recipient_email: "current-recipient@example.invalid",
        payload: {
          version: 1,
          invitation_id: "11111111-1111-4111-8111-111111111111",
          sender_display_name: "<script>alert(1)</script>",
        },
      };
    }
  }
  const gateway = new InvitationGateway([job]);
  const provider = new RecordingProvider(["provider-invitation"]);

  const first = await runEmailWorker(gateway, provider, TEMPLATE_SETTINGS, {
    workerId: "edge-invitation-one",
    now: NOW,
  });
  const replay = await runEmailWorker(gateway, provider, TEMPLATE_SETTINGS, {
    workerId: "edge-invitation-two",
    now: NOW,
  });

  assert.equal(first.sent, 1);
  assert.equal(replay.claimed, 0);
  assert.equal(provider.deliveries.length, 1);
  const delivery = provider.deliveries[0];
  assert.equal(
    delivery.message.recipientEmail,
    "current-recipient@example.invalid",
  );
  assert.equal(delivery.message.subject, "You received a VGU Buddy invitation");
  assert.match(
    delivery.message.textBody,
    /^You've got a new Buddy invitation!/,
  );
  assert.match(
    delivery.message.textBody,
    /<script>alert\(1\)<\/script> would like to connect with you on VGU Buddy\./,
  );
  assert.match(
    delivery.message.textBody,
    /https:\/\/staging\.vgubuddyprogram\.com\/user\/matching\?invitation=11111111/,
  );
  assert.match(
    delivery.message.textBody,
    /This invitation will expire after 7 days\./,
  );
  assert.ok(delivery.message.htmlBody);
  assert.match(
    delivery.message.htmlBody,
    /src="https:\/\/staging\.vgubuddyprogram\.com\/vguBuddy_logo\.png"/,
  );
  assert.match(
    delivery.message.htmlBody,
    /href="https:\/\/staging\.vgubuddyprogram\.com\/user\/matching\?invitation=11111111/,
  );
  assert.match(delivery.message.htmlBody, />View invitation<\/a>/);
  assert.match(
    delivery.message.htmlBody,
    /&lt;script&gt;alert\(1\)&lt;\/script&gt;/,
  );
  assert.equal(
    delivery.message.htmlBody.includes("<script>alert(1)</script>"),
    false,
  );
  assert.match(
    delivery.message.htmlBody,
    /This invitation will expire after 7 days\./,
  );
  assert.equal(
    delivery.message.textBody.includes("private invitation message"),
    false,
  );
  assert.deepEqual(
    provider.deliveries.map(({ idempotencyKey }) => idempotencyKey),
    [job.idempotency_key],
  );
});

test("INV-008 suppresses provider delivery when current recipient is not verified", async () => {
  const job = invitationJob("invite-unverified");
  class UnverifiedGateway extends AtomicFakeGateway {
    override async resolve(claimed: OutboxJob): Promise<OutboxJob> {
      return { ...claimed, recipient_email: null };
    }
  }
  const gateway = new UnverifiedGateway([job]);
  const provider = new RecordingProvider();

  const report = await runEmailWorker(gateway, provider, TEMPLATE_SETTINGS, {
    workerId: "edge-invitation-unverified",
    now: NOW,
  });

  assert.equal(report.terminal_failed, 1);
  assert.equal(provider.deliveries.length, 0);
  assert.equal(
    gateway.stored[0].lastErrorCode,
    "invitation_recipient_unavailable",
  );
});

test("INV-008 rejects malformed resolved payload without exposing it to the provider", async () => {
  const job = invitationJob("invite-malformed");
  class MalformedGateway extends AtomicFakeGateway {
    override async resolve(claimed: OutboxJob): Promise<OutboxJob> {
      return {
        ...claimed,
        payload: {
          version: 1,
          invitation_id: "not-a-uuid",
          sender_display_name: "Sender",
        },
      };
    }
  }
  const gateway = new MalformedGateway([job]);
  const provider = new RecordingProvider();

  const report = await runEmailWorker(gateway, provider, TEMPLATE_SETTINGS, {
    workerId: "edge-invitation-malformed",
    now: NOW,
  });

  assert.equal(report.terminal_failed, 1);
  assert.equal(provider.deliveries.length, 0);
  assert.equal(gateway.stored[0].lastErrorCode, "invitation_payload_invalid");
});

test("INV-008 accepts only the minimal invitation-created reference payload", () => {
  assert.equal(
    invitationIdFromCreationPayload({
      invitation_id: "11111111-1111-4111-8111-111111111111",
    }),
    "11111111-1111-4111-8111-111111111111",
  );
  assert.throws(
    () =>
      invitationIdFromCreationPayload({
        invitation_id: "11111111-1111-4111-8111-111111111111",
        message: "private",
      }),
    /Transactional email template is unavailable/,
  );
  assert.throws(
    () => invitationIdFromCreationPayload({ invitation_id: "not-a-uuid" }),
    /Transactional email template is unavailable/,
  );
});

test("INV-009 resolves current sender and sends one plain-text Start Chatting email", async () => {
  const job = acceptedInvitationJob("accepted-current");
  class AcceptedInvitationGateway extends AtomicFakeGateway {
    override async resolve(claimed: OutboxJob): Promise<OutboxJob> {
      return {
        ...claimed,
        recipient_email: "current-sender@example.invalid",
        payload: {
          version: 1,
          conversation_id: "44444444-4444-4444-8444-444444444444",
          acceptor_display_name: "<script>alert(1)</script>",
        },
      };
    }
  }
  const gateway = new AcceptedInvitationGateway([job]);
  const provider = new RecordingProvider(["provider-accepted"]);

  const first = await runEmailWorker(gateway, provider, TEMPLATE_SETTINGS, {
    workerId: "edge-accepted-one",
    now: NOW,
  });
  const replay = await runEmailWorker(gateway, provider, TEMPLATE_SETTINGS, {
    workerId: "edge-accepted-two",
    now: NOW,
  });

  assert.equal(first.sent, 1);
  assert.equal(replay.claimed, 0);
  assert.equal(provider.deliveries.length, 1);
  const delivery = provider.deliveries[0];
  assert.equal(
    delivery.message.recipientEmail,
    "current-sender@example.invalid",
  );
  assert.equal(
    delivery.message.subject,
    "Your VGU Buddy invitation was accepted",
  );
  assert.match(
    delivery.message.textBody,
    /^<script>alert\(1\)<\/script> accepted your/,
  );
  assert.match(
    delivery.message.textBody,
    /https:\/\/staging\.vgubuddyprogram\.com\/user\/buddy\?conversation=44444444/,
  );
  assert.equal(
    delivery.message.textBody.includes("private invitation message"),
    false,
  );
  assert.deepEqual(
    provider.deliveries.map(({ idempotencyKey }) => idempotencyKey),
    [job.idempotency_key],
  );
});

test("INV-009 suppresses delivery when the original sender is no longer verified", async () => {
  const job = acceptedInvitationJob("accepted-unverified");
  class UnverifiedSenderGateway extends AtomicFakeGateway {
    override async resolve(claimed: OutboxJob): Promise<OutboxJob> {
      return { ...claimed, recipient_email: null };
    }
  }
  const gateway = new UnverifiedSenderGateway([job]);
  const provider = new RecordingProvider();

  const report = await runEmailWorker(gateway, provider, TEMPLATE_SETTINGS, {
    workerId: "edge-accepted-unverified",
    now: NOW,
  });

  assert.equal(report.terminal_failed, 1);
  assert.equal(provider.deliveries.length, 0);
  assert.equal(
    gateway.stored[0].lastErrorCode,
    "accepted_invitation_recipient_unavailable",
  );
});

test("INV-009 accepts only authoritative opaque IDs in the accepted event payload", () => {
  assert.deepEqual(
    acceptedInvitationReferenceFromPayload({
      invitation_id: "11111111-1111-4111-8111-111111111111",
      match_id: "33333333-3333-4333-8333-333333333333",
      conversation_id: "44444444-4444-4444-8444-444444444444",
    }),
    {
      invitationId: "11111111-1111-4111-8111-111111111111",
      matchId: "33333333-3333-4333-8333-333333333333",
      conversationId: "44444444-4444-4444-8444-444444444444",
    },
  );
  assert.throws(
    () =>
      acceptedInvitationReferenceFromPayload({
        invitation_id: "11111111-1111-4111-8111-111111111111",
        match_id: "33333333-3333-4333-8333-333333333333",
        conversation_id: "not-a-uuid",
      }),
    /Transactional email template is unavailable/,
  );
  assert.throws(
    () =>
      acceptedInvitationReferenceFromPayload({
        invitation_id: "11111111-1111-4111-8111-111111111111",
        match_id: "33333333-3333-4333-8333-333333333333",
        conversation_id: "44444444-4444-4444-8444-444444444444",
        message: "private",
      }),
    /Transactional email template is unavailable/,
  );
});

async function verificationJob(suffix: string): Promise<OutboxJob> {
  const tokenBytes = Uint8Array.from(
    { length: 32 },
    (_, index) => (index + suffix.length) % 256,
  );
  const token = encodeBase64Url(tokenBytes);
  const nonce = Uint8Array.from(
    { length: 12 },
    (_, index) => index + suffix.length,
  );
  const key = await crypto.subtle.importKey(
    "raw",
    SEALING_KEY,
    { name: "AES-GCM" },
    false,
    ["encrypt"],
  );
  const sealed = await crypto.subtle.encrypt(
    {
      name: "AES-GCM",
      iv: nonce,
      additionalData: new TextEncoder().encode(
        "vgu-buddy-email-verification-delivery-v1",
      ),
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

function invitationJob(suffix: string): OutboxJob {
  return {
    id: crypto.randomUUID(),
    event_type: "MATCHING_INVITATION_CREATED",
    recipient_email: "creation-snapshot@example.invalid",
    idempotency_key: `matching-invitation-created:${suffix}`,
    payload: { invitation_id: "11111111-1111-4111-8111-111111111111" },
  };
}

function acceptedInvitationJob(suffix: string): OutboxJob {
  return {
    id: crypto.randomUUID(),
    event_type: "MATCHING_INVITATION_ACCEPTED",
    recipient_email: "acceptance-snapshot@example.invalid",
    idempotency_key: `matching-invitation-accepted:${suffix}`,
    payload: {
      invitation_id: "11111111-1111-4111-8111-111111111111",
      match_id: "33333333-3333-4333-8333-333333333333",
      conversation_id: "44444444-4444-4444-8444-444444444444",
    },
  };
}
