// Caches generated-file contents per job/path/revision (sha256) so tab switches
// and re-renders never refetch. Concurrent requests for one file share a fetch.

import { fetchFileText } from "../api/client";
import type { Artifact } from "../api/types";

export type FileRef = Pick<Artifact, "path" | "sha256">;

const MAX_ENTRIES = 300;
const pending = new Map<string, Promise<string>>();
const resolved = new Map<string, string>();

export function fileCacheKey(jobId: string, file: FileRef): string {
  return `${jobId}\u0000${file.path}\u0000${file.sha256}`;
}

/** Synchronously returns the text if it has already been fetched. */
export function peekFileText(jobId: string, file: FileRef): string | undefined {
  return resolved.get(fileCacheKey(jobId, file));
}

/** Fetches (or reuses) the text of a generated file. Failures are not cached. */
export function loadFileText(jobId: string, file: FileRef): Promise<string> {
  const key = fileCacheKey(jobId, file);
  const done = resolved.get(key);
  if (done !== undefined) return Promise.resolve(done);
  let request = pending.get(key);
  if (!request) {
    request = fetchFileText(jobId, file.path).then(
      (text) => {
        pending.delete(key);
        resolved.set(key, text);
        if (resolved.size > MAX_ENTRIES) {
          const oldest = resolved.keys().next().value;
          if (oldest !== undefined) resolved.delete(oldest);
        }
        return text;
      },
      (err: unknown) => {
        pending.delete(key);
        throw err;
      },
    );
    pending.set(key, request);
  }
  return request;
}
