// Fetch-on-mount hook with optional polling, used for health, blueprints and job lists.

import { useCallback, useEffect, useRef, useState } from "react";

import { errorMessage, isAbortError } from "../api/client";

export interface Resource<T> {
  data: T | undefined;
  /** Message of the latest failure (data from an earlier success is kept). */
  error: string | null;
  /** True until the first response (success or failure) arrives. */
  loading: boolean;
  reload: () => void;
}

export interface ResourceOptions<T> {
  /** Delay before the next automatic refresh, or null to stop polling. */
  pollMs?: (data: T | undefined, error: string | null) => number | null;
}

interface State<T> {
  data: T | undefined;
  error: string | null;
  loading: boolean;
}

export function useResource<T>(
  load: (signal: AbortSignal) => Promise<T>,
  options: ResourceOptions<T> = {},
): Resource<T> {
  const [state, setState] = useState<State<T>>({ data: undefined, error: null, loading: true });
  const [nonce, setNonce] = useState(0);

  // Latest callbacks, so callers can pass inline functions without refetch loops.
  const loadRef = useRef(load);
  const pollRef = useRef(options.pollMs);
  useEffect(() => {
    loadRef.current = load;
    pollRef.current = options.pollMs;
  });

  useEffect(() => {
    const controller = new AbortController();
    let timer: number | undefined;
    let latest: T | undefined;

    const schedule = (error: string | null) => {
      const delay = pollRef.current?.(latest, error);
      if (delay != null && delay > 0) timer = window.setTimeout(run, delay);
    };

    function run() {
      loadRef.current(controller.signal).then(
        (data) => {
          if (controller.signal.aborted) return;
          latest = data;
          setState({ data, error: null, loading: false });
          schedule(null);
        },
        (err: unknown) => {
          if (controller.signal.aborted || isAbortError(err)) return;
          const message = errorMessage(err);
          setState((prev) => ({ data: prev.data, error: message, loading: false }));
          schedule(message);
        },
      );
    }

    run();
    return () => {
      controller.abort();
      if (timer !== undefined) window.clearTimeout(timer);
    };
  }, [nonce]);

  const reload = useCallback(() => setNonce((n) => n + 1), []);
  return { ...state, reload };
}
