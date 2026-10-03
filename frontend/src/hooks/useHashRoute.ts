// Minimal hash router: #/ (catalog), #/builds, #/jobs/<id>.

import { useEffect, useMemo, useState } from "react";

export type Route =
  | { name: "catalog" }
  | { name: "builds" }
  | { name: "job"; jobId: string }
  | { name: "not-found"; path: string };

export const routes = {
  catalog: "#/",
  builds: "#/builds",
  job: (jobId: string) => `#/jobs/${encodeURIComponent(jobId)}`,
};

function safeDecode(segment: string): string | null {
  try {
    return decodeURIComponent(segment);
  } catch {
    return null;
  }
}

export function parseHash(hash: string): Route {
  const raw = hash.replace(/^#/, "").split("?")[0] ?? "";
  const path = raw.length > 1 ? raw.replace(/\/+$/, "") : raw;
  if (path === "" || path === "/") return { name: "catalog" };
  if (path === "/builds") return { name: "builds" };
  const match = /^\/jobs\/([^/]+)$/.exec(path);
  const jobId = match?.[1] ? safeDecode(match[1]) : null;
  if (jobId) return { name: "job", jobId };
  return { name: "not-found", path };
}

/** Navigates to a `#/…` href (no-op when already there). */
export function navigate(href: string): void {
  if (window.location.hash !== href) window.location.hash = href.replace(/^#/, "");
}

/** A stable string for keying views by route (resets view state on navigation). */
export function routeKey(route: Route): string {
  switch (route.name) {
    case "job":
      return `job:${route.jobId}`;
    case "not-found":
      return `404:${route.path}`;
    default:
      return route.name;
  }
}

export function useHashRoute(): Route {
  const [hash, setHash] = useState(() => window.location.hash);
  useEffect(() => {
    const sync = () => setHash(window.location.hash);
    window.addEventListener("hashchange", sync);
    sync(); // catch changes between first render and subscription
    return () => window.removeEventListener("hashchange", sync);
  }, []);
  return useMemo(() => parseHash(hash), [hash]);
}
