import { listJobs } from "../api/client";
import type { JobSummary } from "../api/types";
import { isJobActive } from "../lib/status";
import { useResource, type Resource } from "./useResource";

const ACTIVE_POLL_MS = 3000;
const RETRY_MS = 10_000;

/** GET /api/jobs, refreshed while any listed build is still queued or running. */
export function useJobsList(): Resource<JobSummary[]> {
  return useResource(listJobs, {
    pollMs: (jobs, error) => {
      if (error) return RETRY_MS;
      return jobs?.some((job) => isJobActive(job.status)) ? ACTIVE_POLL_MS : null;
    },
  });
}
