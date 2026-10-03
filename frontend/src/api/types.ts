// Vectron API contract (v0). Mirrors backend/src/vectron/domain/*.py and api/*.py.
//
// Endpoints (all JSON unless noted, base path /api):
//   GET  /api/health                                   -> HealthInfo
//   GET  /api/blueprints                               -> BlueprintSummary[]
//   GET  /api/blueprints/{id}                          -> BlueprintDetail
//   POST /api/jobs            body: BuildRequest       -> JobRecord (201)
//   GET  /api/jobs                                     -> JobSummary[] (newest first)
//   GET  /api/jobs/{id}                                -> JobRecord
//   GET  /api/jobs/{id}/events[?after=<seq>]           -> text/event-stream of JobEvent
//        Each SSE message: `id: <seq>` + `data: <JobEvent JSON>`. Replays history, then
//        streams live; the server closes the stream after the terminal job event.
//   GET  /api/jobs/{id}/files/{path}                   -> raw file (artifact path)
//   GET  /api/jobs/{id}/bundle                         -> application/zip (whole project)
//   GET  /api/jobs/{id}/modules/{module_id}/bundle     -> application/zip (one module + core)
//
// Errors: non-2xx responses carry {"detail": string | object}.

export type Category = "air" | "ground" | "maritime" | "sensor" | "c2" | "space";

export interface HealthInfo {
  status: "ok";
  version: string;
  /** Classification banner text shown at the top of the UI, e.g. "UNCLASSIFIED". */
  banner: string;
  llm: {
    provider: "offline" | "anthropic" | "claude-code";
    model: string | null;
    enabled: boolean;
    /** Human readable status, e.g. "Deterministic offline mode" or a config problem. */
    detail: string;
  };
}

export interface OptionChoice {
  value: string;
  label: string;
}

export interface BlueprintOption {
  key: string;
  label: string;
  type: "choice" | "number" | "boolean";
  default: string | number | boolean;
  help: string;
  unit: string;
  choices: OptionChoice[];
  min: number | null;
  max: number | null;
  step: number | null;
}

export interface BlueprintSummary {
  id: string;
  name: string;
  designation: string;
  category: Category;
  summary: string;
  keywords: string[];
  stats: { subsystems: number; modules: number };
  options: BlueprintOption[];
}

export interface BlueprintModule {
  id: string;
  name: string;
  responsibility: string;
  /** Parts-library id when a certified implementation exists, else null (stub). */
  part: string | null;
}

export interface BlueprintSubsystem {
  id: string;
  name: string;
  description: string;
  modules: BlueprintModule[];
}

export interface BlueprintDetail extends BlueprintSummary {
  subsystems: BlueprintSubsystem[];
}

export interface BuildRequest {
  blueprint_id?: string | null;
  /** Free-text mission brief. Required when blueprint_id is omitted. */
  brief?: string;
  options?: Record<string, string | number | boolean>;
}

export type JobStatus = "queued" | "running" | "succeeded" | "failed";
export type TaskStatus = "pending" | "running" | "succeeded" | "failed" | "skipped";

/** Agent roles. `agent` on a task is the display name (e.g. "Commander"). */
export type AgentRole =
  | "planner"
  | "architect"
  | "draftsman"
  | "integrator"
  | "engineer"
  | "inspector"
  | "packager";

export interface TaskRecord {
  id: string;
  role: AgentRole;
  agent: string;
  title: string;
  status: TaskStatus;
  /** Task that spawned this one (agents delegating to agents); null for the root. */
  parent_id: string | null;
  depends_on: string[];
  params: Record<string, unknown>;
  created_at: string;
  started_at: string | null;
  finished_at: string | null;
  summary: string;
  error: string | null;
  duration_ms: number | null;
}

export type ArtifactKind = "source" | "test" | "diagram" | "doc" | "config";

export interface Artifact {
  /** Path inside the generated project, e.g. "src/recon_drone/navigation/gnss_receiver.py". */
  path: string;
  kind: ArtifactKind;
  /** e.g. "text/x-python", "text/vnd.mermaid", "image/svg+xml", "text/markdown", "application/json". */
  media_type: string;
  title: string;
  description: string;
  size: number;
  sha256: string;
  module_id: string | null;
  /** Task id that produced the artifact. */
  producer: string;
}

export interface ModuleBuild {
  id: string;
  name: string;
  subsystem: string;
  class_name: string;
  responsibility: string;
  path: string;
  test_path: string;
  /** "part:<id>" (certified parts library), "stub" (scaffold) or "llm:<model>" (LLM-fabricated). */
  provenance: string;
  notes: string[];
}

export type CheckStatus = "pass" | "warn" | "fail";

export interface InspectionCheck {
  id: string;
  title: string;
  status: CheckStatus;
  detail: string;
  target: string | null;
}

export interface InspectionReport {
  checks: InspectionCheck[];
  counts: Record<CheckStatus, number>;
  passed: boolean;
}

export interface BundleInfo {
  filename: string;
  size: number;
  sha256: string;
  file_count: number;
}

export interface JobProgress {
  total: number;
  pending: number;
  running: number;
  succeeded: number;
  failed: number;
  skipped: number;
}

export interface JobRecord {
  id: string;
  status: JobStatus;
  request: BuildRequest;
  title: string;
  blueprint_id: string | null;
  created_at: string;
  started_at: string | null;
  finished_at: string | null;
  error: string | null;
  llm: { provider: string; model: string | null };
  usage: { calls: number; input_tokens: number; output_tokens: number };
  tasks: TaskRecord[];
  artifacts: Artifact[];
  modules: ModuleBuild[];
  inspection: InspectionReport | null;
  bundle: BundleInfo | null;
  progress: JobProgress;
}

export interface JobSummary {
  id: string;
  status: JobStatus;
  title: string;
  blueprint_id: string | null;
  created_at: string;
  finished_at: string | null;
  progress: JobProgress;
}

export type JobEventType =
  | "job.queued"
  | "job.started"
  | "job.succeeded"
  | "job.failed"
  | "task.queued"
  | "task.started"
  | "task.log"
  | "task.succeeded"
  | "task.failed"
  | "task.skipped"
  | "artifact.created";

export interface JobEvent {
  seq: number;
  ts: string;
  type: JobEventType;
  job_id: string;
  task_id: string | null;
  message: string;
  data: Record<string, unknown>;
}
