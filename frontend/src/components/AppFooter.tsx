import type { HealthInfo } from "../api/types";
import type { Resource } from "../hooks/useResource";

export function AppFooter({ health }: { health: Resource<HealthInfo> }) {
  const version = health.data?.version;
  return (
    <footer className="app-footer">
      <span>
        Vectron{version ? ` v${version}` : ""} · Software factory · Local assets only
      </span>
      {health.data?.llm.detail && (
        <span className="app-footer__detail" title={health.data.llm.detail}>
          Engine: {health.data.llm.detail}
        </span>
      )}
    </footer>
  );
}
