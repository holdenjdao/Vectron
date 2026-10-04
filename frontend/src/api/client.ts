// Typed wrappers around the Vectron HTTP API (see ./types.ts for the contract).

import type {
  BlueprintDetail,
  BlueprintSummary,
  BuildRequest,
  HealthInfo,
  JobRecord,
  JobSummary,
} from "./types";

export const API_BASE = "/api";

/** A failed API call. `message` is ready to show to the user; `status` is 0 for network failures. */
export class ApiError extends Error {
  readonly status: number;
  readonly detail: unknown;

  constructor(status: number, message: string, detail?: unknown) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.detail = detail;
  }
}

export function isAbortError(err: unknown): boolean {
  return err instanceof DOMException && err.name === "AbortError";
}

/** Human-readable message for anything thrown by the API layer (or elsewhere). */
export function errorMessage(err: unknown): string {
  if (err instanceof Error) return err.message;
  if (err && typeof err === "object") {
    const { message, str } = err as { message?: unknown; str?: unknown };
    if (typeof message === "string") return message;
    if (typeof str === "string") return str;
  }
  return String(err);
}

/**
 * Flattens a FastAPI `detail` into one line: plain strings pass through,
 * validation-error lists become "field: message; …", objects use their
 * message-like field or fall back to JSON.
 */
export function formatDetail(detail: unknown): string | null {
  if (detail == null || detail === "") return null;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    const parts = detail.map((item: unknown) => {
      if (item && typeof item === "object") {
        const { loc, msg } = item as { loc?: unknown; msg?: unknown };
        const where = Array.isArray(loc) ? loc.filter((p) => p !== "body").join(".") : "";
        const text = typeof msg === "string" ? msg.replace(/^Value error, /, "") : JSON.stringify(item);
        return where ? `${where}: ${text}` : text;
      }
      return String(item);
    });
    return parts.join("; ") || null;
  }
  if (typeof detail === "object") {
    const record = detail as Record<string, unknown>;
    for (const key of ["message", "msg", "error", "detail"]) {
      const value = record[key];
      if (typeof value === "string" && value) return value;
    }
    try {
      return JSON.stringify(detail);
    } catch {
      return String(detail);
    }
  }
  return String(detail);
}

async function errorFromResponse(res: Response): Promise<ApiError> {
  let detail: unknown;
  try {
    const text = await res.text();
    try {
      detail = (JSON.parse(text) as { detail?: unknown } | null)?.detail;
    } catch {
      // Not JSON: keep short plain-text bodies, ignore HTML error pages.
      const trimmed = text.trim();
      if (trimmed && trimmed.length < 300 && !trimmed.startsWith("<")) detail = trimmed;
    }
  } catch {
    // Body unreadable; fall through to the status line.
  }
  let message = formatDetail(detail);
  if (!message) {
    const status = `HTTP ${res.status}${res.statusText ? ` ${res.statusText}` : ""}`;
    message =
      res.status >= 500 ? `The vectron.ai backend is unavailable or failed (${status}).` : status;
  }
  return new ApiError(res.status, message, detail);
}

async function send(url: string, init: RequestInit): Promise<Response> {
  let res: Response;
  try {
    res = await fetch(url, init);
  } catch (err) {
    if (isAbortError(err)) throw err;
    throw new ApiError(0, "Cannot reach the vectron.ai backend. Check that the API server is running.");
  }
  if (!res.ok) throw await errorFromResponse(res);
  return res;
}

async function requestJson<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  headers.set("Accept", "application/json");
  if (init.body != null && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  const res = await send(API_BASE + path, { ...init, headers });
  try {
    return (await res.json()) as T;
  } catch {
    throw new ApiError(res.status, "The backend returned a malformed response.");
  }
}

// ---------------------------------------------------------------------------
// URL helpers
// ---------------------------------------------------------------------------

const enc = encodeURIComponent;

/** Encodes each segment of an artifact path, keeping the slashes. */
export function encodePath(path: string): string {
  return path.replace(/^\/+/, "").split("/").map(enc).join("/");
}

export function fileUrl(jobId: string, path: string): string {
  return `${API_BASE}/jobs/${enc(jobId)}/files/${encodePath(path)}`;
}

export function bundleUrl(jobId: string): string {
  return `${API_BASE}/jobs/${enc(jobId)}/bundle`;
}

export function moduleBundleUrl(jobId: string, moduleId: string): string {
  return `${API_BASE}/jobs/${enc(jobId)}/modules/${enc(moduleId)}/bundle`;
}

export function eventsUrl(jobId: string, afterSeq?: number): string {
  const query = afterSeq != null ? `?after=${afterSeq}` : "";
  return `${API_BASE}/jobs/${enc(jobId)}/events${query}`;
}

// ---------------------------------------------------------------------------
// Endpoints
// ---------------------------------------------------------------------------

export function getHealth(signal?: AbortSignal): Promise<HealthInfo> {
  return requestJson<HealthInfo>("/health", { signal });
}

export function listBlueprints(signal?: AbortSignal): Promise<BlueprintSummary[]> {
  return requestJson<BlueprintSummary[]>("/blueprints", { signal });
}

export function getBlueprint(id: string, signal?: AbortSignal): Promise<BlueprintDetail> {
  return requestJson<BlueprintDetail>(`/blueprints/${enc(id)}`, { signal });
}

export function createJob(request: BuildRequest, signal?: AbortSignal): Promise<JobRecord> {
  return requestJson<JobRecord>("/jobs", {
    method: "POST",
    body: JSON.stringify(request),
    signal,
  });
}

export function listJobs(signal?: AbortSignal): Promise<JobSummary[]> {
  return requestJson<JobSummary[]>("/jobs", { signal });
}

export function getJob(id: string, signal?: AbortSignal): Promise<JobRecord> {
  return requestJson<JobRecord>(`/jobs/${enc(id)}`, { signal });
}

/** Raw text of a generated file (artifact path inside the job's project). */
export async function fetchFileText(
  jobId: string,
  path: string,
  signal?: AbortSignal,
): Promise<string> {
  // Files can be rewritten while a job runs: always revalidate with the server.
  const res = await send(fileUrl(jobId, path), { signal, cache: "no-cache" });
  return res.text();
}
