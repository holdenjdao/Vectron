import { useEffect, useRef } from "react";

import { getHealth } from "./api/client";
import { AppFooter } from "./components/AppFooter";
import { AppHeader } from "./components/AppHeader";
import { ClassificationBanner } from "./components/ClassificationBanner";
import { ErrorBoundary } from "./components/ErrorBoundary";
import { routeKey, useHashRoute, type Route } from "./hooks/useHashRoute";
import { useResource } from "./hooks/useResource";
import { BuildsView } from "./views/BuildsView";
import { CatalogView } from "./views/CatalogView";
import { JobView } from "./views/JobView";
import { NotFoundView } from "./views/NotFoundView";

/** Retry /api/health while the backend is unreachable, so the header recovers on its own. */
const HEALTH_RETRY_MS = 10_000;

function renderRoute(route: Route) {
  switch (route.name) {
    case "catalog":
      return <CatalogView />;
    case "builds":
      return <BuildsView />;
    case "job":
      return <JobView jobId={route.jobId} />;
    case "not-found":
      return <NotFoundView path={route.path} />;
  }
}

export function App() {
  const route = useHashRoute();
  const key = routeKey(route);
  const mainRef = useRef<HTMLElement>(null);
  const health = useResource(getHealth, {
    pollMs: (_data, error) => (error ? HEALTH_RETRY_MS : null),
  });

  // New view, start at the top.
  useEffect(() => {
    window.scrollTo(0, 0);
  }, [key]);

  const banner = health.data?.banner;

  return (
    <div className="app">
      <ClassificationBanner text={banner} />
      <a
        className="skip-link"
        href="#main"
        onClick={(event) => {
          // Hash routing: focus the content instead of changing the hash.
          event.preventDefault();
          mainRef.current?.focus();
        }}
      >
        Skip to content
      </a>
      <AppHeader route={route} health={health} />
      <main id="main" ref={mainRef} className="app-main" tabIndex={-1}>
        <ErrorBoundary key={key}>{renderRoute(route)}</ErrorBoundary>
      </main>
      <AppFooter health={health} />
      <ClassificationBanner text={banner} position="bottom" />
    </div>
  );
}
