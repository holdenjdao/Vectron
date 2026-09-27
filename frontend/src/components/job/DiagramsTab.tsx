import { useState } from "react";

import { fileUrl } from "../../api/client";
import type { Artifact } from "../../api/types";
import { useFileText } from "../../hooks/useFileText";
import { basename, extension } from "../../lib/format";
import { Callout } from "../Callout";
import { Overlay } from "../Overlay";
import { EmptyState, Loading } from "../States";
import { MermaidView } from "./MermaidView";

const isMermaid = (artifact: Artifact) =>
  artifact.media_type === "text/vnd.mermaid" || extension(artifact.path) === "mmd";

const isSvg = (artifact: Artifact) =>
  artifact.media_type === "image/svg+xml" || extension(artifact.path) === "svg";

/** SVG drawings are shown as images (never inlined), so they cannot run script. */
function SvgImage({ src, alt }: { src: string; alt: string }) {
  const [failed, setFailed] = useState(false);
  if (failed) {
    return (
      <Callout tone="danger" title="Image unavailable">
        The drawing could not be loaded from the server.
      </Callout>
    );
  }
  return <img src={src} alt={alt} decoding="async" onError={() => setFailed(true)} />;
}

function DiagramCard({ jobId, artifact }: { jobId: string; artifact: Artifact }) {
  const [expanded, setExpanded] = useState(false);
  const mermaid = isMermaid(artifact);
  const source = useFileText(jobId, mermaid ? artifact : null);
  const title = artifact.title || basename(artifact.path);
  const url = fileUrl(jobId, artifact.path);

  const sourceLink = (
    <a
      className="btn btn--sm btn--ghost"
      href={url}
      download={basename(artifact.path)}
      aria-label={`Download source of ${title}`}
    >
      Source
    </a>
  );

  const renderDiagram = () => {
    if (mermaid) {
      if (source.status === "ready") return <MermaidView source={source.text} />;
      if (source.status === "error") {
        return (
          <Callout
            tone="danger"
            title="Could not load diagram source"
            actions={
              <button type="button" className="btn btn--sm" onClick={source.retry}>
                Retry
              </button>
            }
          >
            {source.message}
          </Callout>
        );
      }
      return <Loading text="Loading diagram…" compact />;
    }
    if (isSvg(artifact)) {
      // The revision query avoids a stale cached drawing if the file is regenerated.
      return <SvgImage src={`${url}?rev=${encodeURIComponent(artifact.sha256.slice(0, 16))}`} alt={title} />;
    }
    return <EmptyState compact text="No preview" hint="Download the source to view this diagram." />;
  };

  return (
    <article className="diagram-card">
      <header className="diagram-card__head">
        <div className="diagram-card__heading">
          <h3 className="diagram-card__title">{title}</h3>
          {artifact.description && <p className="diagram-card__desc">{artifact.description}</p>}
          <p className="diagram-card__path">{artifact.path}</p>
        </div>
        <div className="diagram-card__actions">
          {sourceLink}
          <button
            type="button"
            className="btn btn--sm btn--ghost"
            onClick={() => setExpanded(true)}
            aria-label={`Expand ${title} to full screen`}
          >
            Expand
          </button>
        </div>
      </header>
      <div className="diagram-canvas canvas">{renderDiagram()}</div>
      {expanded && (
        <Overlay
          title={title}
          onClose={() => setExpanded(false)}
          actions={sourceLink}
          bodyClassName="overlay__body--diagram canvas"
        >
          <div className="diagram-full">{renderDiagram()}</div>
        </Overlay>
      )}
    </article>
  );
}

/** Diagram artifacts: Mermaid sources rendered in the browser, SVG drawings as images. */
export function DiagramsTab({ jobId, diagrams }: { jobId: string; diagrams: Artifact[] }) {
  if (diagrams.length === 0) {
    return (
      <EmptyState text="Awaiting output…" hint="The Draftsman's diagrams appear here as they are drawn." />
    );
  }
  return (
    <div className="diagram-list">
      {diagrams.map((artifact) => (
        <DiagramCard key={artifact.path} jobId={jobId} artifact={artifact} />
      ))}
    </div>
  );
}
