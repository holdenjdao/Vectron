import type { HealthInfo } from "../api/types";
import { routes, type Route } from "../hooks/useHashRoute";
import type { Resource } from "../hooks/useResource";
import { cx } from "../lib/cx";
import { Logo } from "./Logo";

interface Props {
  route: Route;
  health: Resource<HealthInfo>;
}

export function AppHeader({ route, health }: Props) {
  const section = route.name === "catalog" ? "catalog" : route.name === "not-found" ? null : "builds";
  return (
    <header className="app-header">
      <a className="brand" href={routes.catalog} aria-label="Vectron software factory — catalog">
        <Logo />
        <span className="brand__word">VECTRON</span>
        <span className="brand__sub">SOFTWARE FACTORY</span>
      </a>
      <nav className="nav" aria-label="Primary">
        <a
          className="nav__link"
          href={routes.catalog}
          aria-current={section === "catalog" ? "page" : undefined}
        >
          Catalog
        </a>
        <a
          className="nav__link"
          href={routes.builds}
          aria-current={section === "builds" ? "page" : undefined}
        >
          Builds
        </a>
      </nav>
      <div className="app-header__right">
        <EngineChip health={health} />
      </div>
    </header>
  );
}

/** Which code-generation engine the backend is running: deterministic offline mode or Claude. */
export function EngineChip({ health }: { health: Resource<HealthInfo> }) {
  if (!health.data) {
    if (health.loading) {
      return <span className="chip engine-chip">Engine · …</span>;
    }
    return (
      <span className="chip chip--danger engine-chip" title={health.error ?? undefined}>
        <span className="chip__dot" aria-hidden="true" />
        Engine · Unreachable
        <span className="sr-only">: {health.error}</span>
      </span>
    );
  }
  const { llm } = health.data;
  const online = llm.provider !== "offline" && llm.enabled;
  const source = llm.provider === "claude-code" ? "Claude (subscription)" : "Claude";
  const label = online
    ? `Engine · ${source}${llm.model ? ` · ${llm.model}` : ""}`
    : "Engine · Offline";
  return (
    <span className={cx("chip", "engine-chip", online && "chip--accent")} title={llm.detail}>
      <span className="chip__dot" aria-hidden="true" />
      {label}
      {llm.detail && <span className="sr-only">: {llm.detail}</span>}
    </span>
  );
}
