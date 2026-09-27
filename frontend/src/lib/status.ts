// Shared metadata for job/task statuses, agent roles and blueprint categories.

import type { AgentRole, Category, JobProgress, JobStatus, TaskStatus } from "../api/types";

export function isJobTerminal(status: JobStatus): boolean {
  return status === "succeeded" || status === "failed";
}

export function isJobActive(status: JobStatus): boolean {
  return status === "queued" || status === "running";
}

/** Tasks that have finished one way or another. */
export function doneCount(progress: JobProgress): number {
  return progress.succeeded + progress.failed + progress.skipped;
}

export const JOB_STATUS_LABEL: Record<JobStatus, string> = {
  queued: "Queued",
  running: "Running",
  succeeded: "Succeeded",
  failed: "Failed",
};

export const TASK_STATUS_LABEL: Record<TaskStatus, string> = {
  pending: "Pending",
  running: "Running",
  succeeded: "Succeeded",
  failed: "Failed",
  skipped: "Skipped",
};

export const CATEGORY_LABEL: Record<Category, string> = {
  air: "Air",
  ground: "Ground",
  maritime: "Maritime",
  sensor: "Sensor",
  c2: "C2",
  space: "Space",
};

const ROLES: readonly AgentRole[] = [
  "planner",
  "architect",
  "draftsman",
  "integrator",
  "engineer",
  "inspector",
  "packager",
];

/** Normalises a task role for styling (`data-role`); unknown roles render neutral. */
export function roleKey(role: string): AgentRole | "unknown" {
  return (ROLES as readonly string[]).includes(role) ? (role as AgentRole) : "unknown";
}

/** The factory's chain of command as pipeline stages (agents within a stage work in parallel). */
export const CHAIN_OF_COMMAND: { role: AgentRole; name: string }[][] = [
  [{ role: "planner", name: "Commander" }],
  [{ role: "architect", name: "Architect" }],
  [
    { role: "draftsman", name: "Draftsman" },
    { role: "integrator", name: "Integrator" },
    { role: "engineer", name: "Engineers" },
  ],
  [{ role: "inspector", name: "Inspector" }],
  [{ role: "packager", name: "Quartermaster" }],
];
