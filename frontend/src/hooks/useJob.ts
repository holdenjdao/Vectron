// Live view of one build job: the JobRecord snapshot (GET /api/jobs/{id}) kept
// fresh by the job's server-sent event stream, plus the event log itself.

import { useCallback, useEffect, useRef, useState } from "react";

import { ApiError, errorMessage, eventsUrl, getJob, isAbortError } from "../api/client";
import type { JobEvent, JobEventType, JobRecord } from "../api/types";
import { isJobTerminal } from "../lib/status";

export type StreamState = "connecting" | "live" | "reconnecting" | "ended" | "unavailable";

export interface JobFeed {
  job: JobRecord | null;
  /** Failure of the latest snapshot fetch (status 0 = network), if any. */
  error: { message: string; status: number } | null;
  /** Every event received so far, ordered by `seq`, without duplicates. */
  events: JobEvent[];
  stream: StreamState;
  /** Refetch the snapshot now. */
  refresh: () => void;
}

/** Refetch the snapshot this long after the last event of a burst… */
const REFRESH_DEBOUNCE_MS = 200;
/** …but never let a continuous stream delay it by more than this. */
const REFRESH_MAX_WAIT_MS = 1000;
/** Events are appended to the log in small batches (history replays arrive in bursts). */
const EVENT_BATCH_MS = 40;
/** Safety net if the stream silently stalls (e.g. a buffering proxy): poll when idle this long. */
const IDLE_POLL_MS = 10_000;

const EVENT_TYPES: JobEventType[] = [
  "job.queued",
  "job.started",
  "job.succeeded",
  "job.failed",
  "task.queued",
  "task.started",
  "task.log",
  "task.succeeded",
  "task.failed",
  "task.skipped",
  "artifact.created",
];

const REFRESHING_EVENT = /^(job|task|artifact)\./;

function isTerminalEvent(type: string): boolean {
  return type === "job.succeeded" || type === "job.failed";
}

function parseEvent(raw: unknown): JobEvent | null {
  if (typeof raw !== "string") return null;
  try {
    const value = JSON.parse(raw) as Partial<JobEvent> | null;
    if (!value || typeof value.seq !== "number" || typeof value.type !== "string") return null;
    return {
      seq: value.seq,
      ts: typeof value.ts === "string" ? value.ts : "",
      type: value.type,
      job_id: typeof value.job_id === "string" ? value.job_id : "",
      task_id: typeof value.task_id === "string" ? value.task_id : null,
      message: typeof value.message === "string" ? value.message : "",
      data: value.data && typeof value.data === "object" ? value.data : {},
    };
  } catch {
    return null;
  }
}

function mergeEvents(prev: JobEvent[], batch: JobEvent[]): JobEvent[] {
  const next = prev.concat(batch);
  for (let i = Math.max(1, prev.length); i < next.length; i += 1) {
    if (next[i]!.seq < next[i - 1]!.seq) return next.sort((a, b) => a.seq - b.seq);
  }
  return next;
}

export function useJob(jobId: string): JobFeed {
  const [job, setJob] = useState<JobRecord | null>(null);
  const [error, setError] = useState<JobFeed["error"]>(null);
  const [events, setEvents] = useState<JobEvent[]>([]);
  const [stream, setStream] = useState<StreamState>("connecting");
  const refreshRef = useRef<() => void>(() => undefined);

  useEffect(() => {
    let disposed = false;
    let terminal = false;
    let missing = false; // 404: the job does not exist, stop polling
    let source: EventSource | null = null;
    let streamErrored = false;
    let lastActivity = Date.now();

    setJob(null);
    setError(null);
    setEvents((prev) => (prev.length ? [] : prev));
    setStream("connecting");

    const closeStream = (state: StreamState) => {
      source?.close();
      source = null;
      setStream(state);
    };

    // -- Snapshot fetching: requests never overlap; a request made while one is
    //    in flight is queued, so the newest server state always lands last.
    let inFlight: AbortController | null = null;
    let queued = false;

    const fetchJob = () => {
      if (disposed) return;
      if (inFlight) {
        queued = true;
        return;
      }
      const controller = new AbortController();
      inFlight = controller;
      lastActivity = Date.now();
      getJob(jobId, controller.signal)
        .then((record) => {
          if (disposed) return;
          setJob(record);
          setError(null);
          missing = false;
          terminal = isJobTerminal(record.status);
          // A stream that is failing for a finished job has nothing left to deliver.
          if (terminal && source && streamErrored) closeStream("ended");
        })
        .catch((err: unknown) => {
          if (disposed || isAbortError(err)) return;
          const status = err instanceof ApiError ? err.status : 0;
          missing = status === 404;
          setError({ message: errorMessage(err), status });
        })
        .finally(() => {
          if (inFlight === controller) inFlight = null;
          if (queued && !disposed) {
            queued = false;
            fetchJob();
          }
        });
    };

    // -- Debounced refresh with a maximum wait.
    let refreshTimer: number | undefined;
    let firstRequestAt = 0;

    const scheduleRefresh = () => {
      const now = Date.now();
      if (refreshTimer !== undefined) {
        if (now - firstRequestAt >= REFRESH_MAX_WAIT_MS) return; // pending refresh fires shortly
        window.clearTimeout(refreshTimer);
      } else {
        firstRequestAt = now;
      }
      refreshTimer = window.setTimeout(() => {
        refreshTimer = undefined;
        fetchJob();
      }, REFRESH_DEBOUNCE_MS);
    };

    const refreshNow = () => {
      if (refreshTimer !== undefined) window.clearTimeout(refreshTimer);
      refreshTimer = undefined;
      fetchJob();
    };
    refreshRef.current = refreshNow;

    // -- Event log: dedupe by seq, append in small batches.
    const seen = new Set<number>();
    let batch: JobEvent[] = [];
    let batchTimer: number | undefined;

    const flushBatch = () => {
      batchTimer = undefined;
      if (disposed || batch.length === 0) return;
      const items = batch;
      batch = [];
      setEvents((prev) => mergeEvents(prev, items));
    };

    const onEvent = (message: MessageEvent) => {
      if (disposed) return;
      lastActivity = Date.now();
      const event = parseEvent(message.data);
      if (!event || seen.has(event.seq)) return;
      seen.add(event.seq);
      batch.push(event);
      batchTimer ??= window.setTimeout(flushBatch, EVENT_BATCH_MS);

      if (isTerminalEvent(event.type)) {
        terminal = true;
        refreshNow();
        closeStream("ended"); // the server ends the stream here; don't let EventSource reconnect
      } else if (REFRESHING_EVENT.test(event.type)) {
        scheduleRefresh();
      }
    };

    // -- The stream. The server replays the full history first, so the log also
    //    fills for jobs that finished long ago.
    const es = new EventSource(eventsUrl(jobId));
    source = es;
    es.onmessage = onEvent;
    // Also accept named SSE events, in case the server tags messages with `event:`.
    for (const type of EVENT_TYPES) es.addEventListener(type, onEvent);

    es.onopen = () => {
      if (disposed || source !== es) return;
      setStream("live");
      if (streamErrored) {
        streamErrored = false;
        fetchJob(); // resync after a reconnect
      }
    };

    es.onerror = () => {
      if (disposed || source !== es) return;
      streamErrored = true;
      if (es.readyState === EventSource.CLOSED) {
        // The browser gave up for good (HTTP error or non-SSE response).
        closeStream(terminal ? "ended" : "unavailable");
        if (!missing) fetchJob();
        return;
      }
      if (terminal) {
        closeStream("ended");
        return;
      }
      // EventSource retries by itself; meanwhile resync the snapshot. If the job
      // turns out to be finished, fetchJob closes the stream.
      setStream("reconnecting");
      fetchJob();
    };

    const idlePoll = window.setInterval(() => {
      if (!terminal && !missing && Date.now() - lastActivity >= IDLE_POLL_MS) fetchJob();
    }, IDLE_POLL_MS / 2);

    fetchJob();

    return () => {
      disposed = true;
      es.close();
      source = null;
      inFlight?.abort();
      window.clearInterval(idlePoll);
      if (refreshTimer !== undefined) window.clearTimeout(refreshTimer);
      if (batchTimer !== undefined) window.clearTimeout(batchTimer);
      refreshRef.current = () => undefined;
    };
  }, [jobId]);

  const refresh = useCallback(() => refreshRef.current(), []);
  return { job, error, events, stream, refresh };
}
