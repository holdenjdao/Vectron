import { EmptyState } from "../components/States";
import { useDocumentTitle } from "../hooks/useDocumentTitle";
import { routes } from "../hooks/useHashRoute";

export function NotFoundView({ path }: { path: string }) {
  useDocumentTitle("Not found");
  return (
    <EmptyState text="Unknown route" hint={<span className="mono">{path}</span>}>
      <a className="btn btn--primary" href={routes.catalog}>
        Back to catalog
      </a>
    </EmptyState>
  );
}
