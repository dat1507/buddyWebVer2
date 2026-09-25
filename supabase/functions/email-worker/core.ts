export const DEFAULT_BATCH_SIZE = 20;
export const MAX_BATCH_SIZE = 100;
export const DELIVERY_CONCURRENCY = 5;
export const RESEND_EMAIL_ENDPOINT = "https://api.resend.com/emails";

const PROVIDER_TIMEOUT_MS = 10_000;
const MAX_PROVIDER_RESPONSE_BYTES = 4_096;
const VERIFICATION_EVENT = "EMAIL_VERIFICATION_REQUESTED";
const VERIFICATION_AAD = new TextEncoder().encode(
  "vgu-buddy-email-verification-delivery-v1",
);
const BASE64URL_PATTERN = /^[A-Za-z0-9_-]+$/;
const ERROR_CODE_PATTERN = /^[a-z0-9_]{1,100}$/;

export interface OutboxJob {
  id: string;
  event_type: string;
  recipient_email: string;
  idempotency_key: string;
  payload: Record<string, unknown>;
}

export interface OutboundEmail {
  recipientEmail: string;
  subject: string;
  textBody: string;
}

export type FinalizeOutcome = "sent" | "retry" | "failed" | "skipped";

export interface OutboxGateway {
  claim(workerId: string, batchSize: number): Promise<readonly OutboxJob[]>;
  complete(
    jobId: string,
    workerId: string,
    providerMessageId: string,
  ): Promise<FinalizeOutcome>;
  fail(
    jobId: string,
    workerId: string,
    retryable: boolean,
    errorCode: string,
  ): Promise<FinalizeOutcome>;
}

export interface EmailProvider {
  send(message: OutboundEmail, idempotencyKey: string): Promise<string>;
}

export interface TemplateSettings {
  publicAppBaseUrl: string;
  sealingKey: Uint8Array;
}

export interface WorkerReport {
  claimed: number;
  sent: number;
  retry_scheduled: number;
  terminal_failed: number;
  skipped: number;
}

export class DeliveryFailure extends Error {
  readonly retryable: boolean;
  readonly errorCode: string;

  constructor(retryable: boolean, errorCode: string) {
    super("Email delivery failed.");
    this.name = "DeliveryFailure";
    this.retryable = retryable;
    this.errorCode = safeErrorCode(errorCode, "provider_unavailable");
  }
}

export class TemplateFailure extends Error {
  readonly errorCode: string;

  constructor(errorCode: string) {
    super("Transactional email template is unavailable.");
    this.name = "TemplateFailure";
    this.errorCode = safeErrorCode(errorCode, "template_render_failed");
  }
}

export class ResendEmailProvider implements EmailProvider {
  readonly #apiKey: string;
  readonly #fromAddress: string;
  readonly #fetch: typeof fetch;

  constructor(apiKey: string, fromAddress: string, fetchImplementation = fetch) {
    if (!apiKey.trim()) {
      throw new Error("Email provider configuration is unavailable.");
    }
    assertSafeEmailAddress(fromAddress);
    this.#apiKey = apiKey;
    this.#fromAddress = fromAddress.trim();
    this.#fetch = fetchImplementation;
  }

  async send(message: OutboundEmail, idempotencyKey: string): Promise<string> {
    assertSafeEmailAddress(message.recipientEmail);
    if (!message.subject.trim() || /[\r\n]/.test(message.subject) || !message.textBody.trim()) {
      throw new DeliveryFailure(false, "invalid_email_content");
    }
    const normalizedKey = idempotencyKey.trim();
    if (!normalizedKey || normalizedKey.length > 256 || /[\r\n]/.test(normalizedKey)) {
      throw new DeliveryFailure(false, "invalid_idempotency_key");
    }

    let response: Response;
    try {
      response = await this.#fetch(RESEND_EMAIL_ENDPOINT, {
        method: "POST",
        redirect: "error",
        signal: AbortSignal.timeout(PROVIDER_TIMEOUT_MS),
        headers: {
          Authorization: `Bearer ${this.#apiKey}`,
          "Content-Type": "application/json",
          "Idempotency-Key": normalizedKey,
          "User-Agent": "vgu-buddy-edge-email-worker/0.1",
        },
        body: JSON.stringify({
          from: this.#fromAddress,
          to: [message.recipientEmail],
          subject: message.subject,
          text: message.textBody,
        }),
      });
    } catch {
      throw new DeliveryFailure(true, "provider_unavailable");
    }

    if (!response.ok) {
      const retryable = [408, 409, 425, 429].includes(response.status) || response.status >= 500;
      throw new DeliveryFailure(retryable, `provider_http_${response.status}`);
    }

    let providerMessageId: unknown;
    try {
      const body = await readBoundedText(response, MAX_PROVIDER_RESPONSE_BYTES);
      const parsed: unknown = JSON.parse(body);
      providerMessageId = isRecord(parsed) ? parsed.id : undefined;
    } catch {
      providerMessageId = undefined;
    }
    if (
      typeof providerMessageId !== "string" ||
      !providerMessageId.trim() ||
      providerMessageId.length > 200 ||
      /[\r\n]/.test(providerMessageId)
    ) {
      throw new DeliveryFailure(true, "invalid_provider_response");
    }
    return providerMessageId.trim();
  }
}

export function decodeSealingKey(value: string): Uint8Array {
  if (!/^[A-Za-z0-9_-]+={0,2}$/.test(value)) {
    throw new Error("Email verification delivery configuration is unavailable.");
  }
  const unpadded = value.replace(/=+$/, "");
  const canonicalPadding = "=".repeat((4 - unpadded.length % 4) % 4);
  if (value !== unpadded && value !== unpadded + canonicalPadding) {
    throw new Error("Email verification delivery configuration is unavailable.");
  }
  const decoded = decodeBase64Url(unpadded);
  if (decoded.byteLength !== 32) {
    throw new Error("Email verification delivery configuration is unavailable.");
  }
  return decoded;
}

export async function renderEmail(
  job: OutboxJob,
  settings: TemplateSettings,
  now = new Date(),
): Promise<OutboundEmail> {
  if (job.event_type !== VERIFICATION_EVENT) {
    throw new TemplateFailure("template_unregistered");
  }
  return await renderVerificationEmail(job, settings, now);
}

export async function runEmailWorker(
  gateway: OutboxGateway,
  provider: EmailProvider,
  templates: TemplateSettings,
  options: {
    batchSize?: number;
    deliveryConcurrency?: number;
    workerId?: string;
    now?: Date;
  } = {},
): Promise<WorkerReport> {
  const batchSize = options.batchSize ?? DEFAULT_BATCH_SIZE;
  const deliveryConcurrency = options.deliveryConcurrency ?? DELIVERY_CONCURRENCY;
  if (!Number.isInteger(batchSize) || batchSize < 1 || batchSize > MAX_BATCH_SIZE) {
    throw new Error("Email outbox batch size is invalid.");
  }
  if (
    !Number.isInteger(deliveryConcurrency) ||
    deliveryConcurrency < 1 ||
    deliveryConcurrency > batchSize
  ) {
    throw new Error("Email delivery concurrency is invalid.");
  }
  const workerId = options.workerId ?? `edge-email-worker-${crypto.randomUUID()}`;
  if (!workerId || workerId.length > 100 || /[\r\n]/.test(workerId)) {
    throw new Error("Email outbox worker ID is invalid.");
  }

  const jobs = await gateway.claim(workerId, batchSize);
  if (jobs.length > batchSize) {
    throw new Error("Email outbox claim exceeded its batch bound.");
  }
  const outcomes = await mapWithConcurrency(
    jobs,
    deliveryConcurrency,
    async (job): Promise<FinalizeOutcome> => {
      try {
        const message = await renderEmail(job, templates, options.now ?? new Date());
        const providerMessageId = await provider.send(message, job.idempotency_key);
        return await gateway.complete(job.id, workerId, providerMessageId);
      } catch (error) {
        const failure = normalizeFailure(error);
        return await gateway.fail(
          job.id,
          workerId,
          failure.retryable,
          failure.errorCode,
        );
      }
    },
  );

  return {
    claimed: jobs.length,
    sent: outcomes.filter((outcome) => outcome === "sent").length,
    retry_scheduled: outcomes.filter((outcome) => outcome === "retry").length,
    terminal_failed: outcomes.filter((outcome) => outcome === "failed").length,
    skipped: outcomes.filter((outcome) => outcome === "skipped").length,
  };
}

export async function constantTimeSecretEquals(actual: string, expected: string): Promise<boolean> {
  const encoder = new TextEncoder();
  const [actualDigest, expectedDigest] = await Promise.all([
    crypto.subtle.digest("SHA-256", encoder.encode(actual)),
    crypto.subtle.digest("SHA-256", encoder.encode(expected)),
  ]);
  const actualBytes = new Uint8Array(actualDigest);
  const expectedBytes = new Uint8Array(expectedDigest);
  let difference = 0;
  for (let index = 0; index < actualBytes.length; index += 1) {
    difference |= actualBytes[index] ^ expectedBytes[index];
  }
  return difference === 0;
}

async function renderVerificationEmail(
  job: OutboxJob,
  settings: TemplateSettings,
  now: Date,
): Promise<OutboundEmail> {
  const expectedKeys = ["expires_at", "nonce", "sealed_value", "version"];
  if (Object.keys(job.payload).sort().join("|") !== expectedKeys.join("|")) {
    throw new TemplateFailure("verification_payload_invalid");
  }
  if (job.payload.version !== 1) {
    throw new TemplateFailure("verification_payload_invalid");
  }

  const expiresAt = job.payload.expires_at;
  if (
    typeof expiresAt !== "string" ||
    !/(?:Z|[+-]\d{2}:\d{2})$/.test(expiresAt) ||
    !Number.isFinite(Date.parse(expiresAt)) ||
    Date.parse(expiresAt) <= now.getTime()
  ) {
    throw new TemplateFailure("verification_link_expired");
  }

  try {
    const nonce = decodeBase64Url(job.payload.nonce);
    const sealedValue = decodeBase64Url(job.payload.sealed_value);
    if (nonce.byteLength !== 12) {
      throw new Error("invalid nonce");
    }
    const key = await crypto.subtle.importKey(
      "raw",
      Uint8Array.from(settings.sealingKey).buffer,
      { name: "AES-GCM" },
      false,
      ["decrypt"],
    );
    const plaintext = await crypto.subtle.decrypt(
      {
        name: "AES-GCM",
        iv: Uint8Array.from(nonce).buffer,
        additionalData: Uint8Array.from(VERIFICATION_AAD).buffer,
      },
      key,
      Uint8Array.from(sealedValue).buffer,
    );
    const token = new TextDecoder("utf-8", { fatal: true }).decode(plaintext);
    const tokenBytes = decodeBase64Url(token);
    if (token.length !== 43 || tokenBytes.byteLength !== 32) {
      throw new Error("invalid token");
    }
    const appOrigin = normalizePublicAppOrigin(settings.publicAppBaseUrl);
    const link = `${appOrigin}/verify-email?token=${encodeURIComponent(token)}`;
    return {
      recipientEmail: job.recipient_email,
      subject: "Verify your VGU Buddy email",
      textBody:
        "Verify your email address for VGU Buddy by opening this link:\n\n" +
        `${link}\n\n` +
        "This link expires 15 minutes after it was requested. " +
        "If you did not request this email, you can ignore it.",
    };
  } catch (error) {
    if (error instanceof TemplateFailure) {
      throw error;
    }
    throw new TemplateFailure("verification_payload_invalid");
  }
}

function normalizePublicAppOrigin(value: string): string {
  let parsed: URL;
  try {
    parsed = new URL(value);
  } catch {
    throw new TemplateFailure("verification_configuration_invalid");
  }
  if (
    parsed.protocol !== "https:" ||
    parsed.username ||
    parsed.password ||
    parsed.pathname !== "/" ||
    parsed.search ||
    parsed.hash
  ) {
    throw new TemplateFailure("verification_configuration_invalid");
  }
  return parsed.origin;
}

function decodeBase64Url(value: unknown): Uint8Array {
  if (typeof value !== "string" || !value || !BASE64URL_PATTERN.test(value)) {
    throw new Error("invalid base64url value");
  }
  const padded = value.replaceAll("-", "+").replaceAll("_", "/") + "=".repeat((4 - value.length % 4) % 4);
  const binary = atob(padded);
  const decoded = Uint8Array.from(binary, (character) => character.charCodeAt(0));
  if (encodeBase64Url(decoded) !== value) {
    throw new Error("non-canonical base64url value");
  }
  return decoded;
}

export function encodeBase64Url(value: Uint8Array): string {
  let binary = "";
  for (const byte of value) {
    binary += String.fromCharCode(byte);
  }
  return btoa(binary).replaceAll("+", "-").replaceAll("/", "_").replace(/=+$/, "");
}

function assertSafeEmailAddress(value: string): void {
  const normalized = value.trim();
  if (!normalized || normalized.length > 320 || /[\r\n]/.test(normalized)) {
    throw new Error("Email address configuration is unavailable.");
  }
}

function safeErrorCode(value: string, fallback: string): string {
  return ERROR_CODE_PATTERN.test(value) ? value : fallback;
}

function normalizeFailure(error: unknown): { retryable: boolean; errorCode: string } {
  if (error instanceof DeliveryFailure) {
    return { retryable: error.retryable, errorCode: error.errorCode };
  }
  if (error instanceof TemplateFailure) {
    return { retryable: false, errorCode: error.errorCode };
  }
  return { retryable: true, errorCode: "worker_unavailable" };
}

async function mapWithConcurrency<T, R>(
  values: readonly T[],
  concurrency: number,
  operation: (value: T) => Promise<R>,
): Promise<R[]> {
  const results = new Array<R>(values.length);
  let cursor = 0;
  async function consume(): Promise<void> {
    while (cursor < values.length) {
      const index = cursor;
      cursor += 1;
      results[index] = await operation(values[index]);
    }
  }
  await Promise.all(
    Array.from({ length: Math.min(concurrency, values.length) }, async () => await consume()),
  );
  return results;
}

async function readBoundedText(response: Response, maximumBytes: number): Promise<string> {
  if (response.body === null) {
    return "";
  }
  const reader = response.body.getReader();
  const chunks: Uint8Array[] = [];
  let size = 0;
  while (true) {
    const { done, value } = await reader.read();
    if (done) {
      break;
    }
    size += value.byteLength;
    if (size > maximumBytes) {
      await reader.cancel();
      throw new Error("Provider response exceeded its size limit.");
    }
    chunks.push(value);
  }
  const body = new Uint8Array(size);
  let offset = 0;
  for (const chunk of chunks) {
    body.set(chunk, offset);
    offset += chunk.byteLength;
  }
  return new TextDecoder("utf-8", { fatal: true }).decode(body);
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}
