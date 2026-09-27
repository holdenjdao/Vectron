import { useCallback, useEffect, useState } from "react";

import { errorMessage } from "../api/client";
import { fileCacheKey, loadFileText, peekFileText, type FileRef } from "../lib/fileCache";

export type FileText =
  | { status: "idle" }
  | { status: "loading" }
  | { status: "ready"; text: string }
  | { status: "error"; message: string };

interface Result {
  key: string;
  attempt: number;
  value: FileText;
}

/** Loads the text of a generated file (cached per job/path/sha256). Pass null to skip. */
export function useFileText(
  jobId: string,
  file: FileRef | null | undefined,
): FileText & { retry: () => void } {
  const key = file ? fileCacheKey(jobId, file) : null;
  const cached = file ? peekFileText(jobId, file) : undefined;
  const [result, setResult] = useState<Result | null>(null);
  const [attempt, setAttempt] = useState(0);
  const retry = useCallback(() => setAttempt((n) => n + 1), []);

  // `key` already captures jobId + path + sha256; the `file` object itself gets a
  // new identity on every job refetch, so it is deliberately not a dependency.
  useEffect(() => {
    if (!file || !key || cached !== undefined) return;
    let cancelled = false;
    const settle = (value: FileText) => {
      if (!cancelled) setResult({ key, attempt, value });
    };
    loadFileText(jobId, file).then(
      (text) => settle({ status: "ready", text }),
      (err: unknown) => settle({ status: "error", message: errorMessage(err) }),
    );
    return () => {
      cancelled = true;
    };
  }, [key, attempt, cached]);

  if (!file) return { status: "idle", retry };
  if (cached !== undefined) return { status: "ready", text: cached, retry };
  if (result && result.key === key && result.attempt === attempt) return { ...result.value, retry };
  return { status: "loading", retry };
}
