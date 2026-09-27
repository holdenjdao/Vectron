import { useState } from "react";

import { listBlueprints } from "../api/client";
import { BlueprintCard } from "../components/catalog/BlueprintCard";
import { ChainOfCommand } from "../components/catalog/ChainOfCommand";
import { MissionBrief } from "../components/catalog/MissionBrief";
import { RecentBuilds } from "../components/catalog/RecentBuilds";
import { Callout } from "../components/Callout";
import { EmptyState, Loading } from "../components/States";
import { useDocumentTitle } from "../hooks/useDocumentTitle";
import { useJobsList } from "../hooks/useJobsList";
import { useResource } from "../hooks/useResource";

export function CatalogView() {
  useDocumentTitle("Catalog");
  const blueprints = useResource(listBlueprints);
  const jobs = useJobsList();
  const [brief, setBrief] = useState("");
  const count = blueprints.data?.length;

  let grid;
  if (blueprints.loading) {
    grid = <Loading text="Loading catalog…" />;
  } else if (!blueprints.data) {
    grid = (
      <Callout
        tone="danger"
        title="Catalog unavailable"
        actions={
          <button type="button" className="btn btn--sm" onClick={blueprints.reload}>
            Retry
          </button>
        }
      >
        {blueprints.error}
      </Callout>
    );
  } else if (blueprints.data.length === 0) {
    grid = <EmptyState text="No blueprints installed" hint="You can still build from a mission brief." />;
  } else {
    grid = (
      <div className="bp-grid">
        {blueprints.data.map((blueprint) => (
          <BlueprintCard key={blueprint.id} blueprint={blueprint} brief={brief} />
        ))}
      </div>
    );
  }

  return (
    <div className="catalog">
      <div className="catalog__main">
        <header className="intro">
          <h1 className="eyebrow">System catalog</h1>
          <p className="intro__lede">
            Select a system. Vectron's agents will architect it, draft its diagrams and fabricate
            modular code.
          </p>
          <ChainOfCommand />
        </header>

        <MissionBrief brief={brief} onBriefChange={setBrief} />

        <section aria-labelledby="blueprints-title">
          <div className="section-head">
            <h2 id="blueprints-title" className="panel__title">
              Blueprints
            </h2>
            <span className="section-head__rule" aria-hidden="true" />
            {count != null && (
              <span className="vx-label">
                {count} {count === 1 ? "system" : "systems"}
              </span>
            )}
          </div>
          {grid}
        </section>
      </div>

      <aside className="catalog__rail" aria-label="Recent builds">
        <RecentBuilds jobs={jobs} />
      </aside>
    </div>
  );
}
