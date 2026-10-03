import { useEffect, useState } from "react";

import { errorMessage } from "../../api/client";
import { renderMermaid } from "../../lib/mermaid";
import { Callout } from "../Callout";
import { Loading } from "../States";

type RenderState =
  | { status: "rendering" }
  | { status: "ready"; svg: string }
  | { status: "error"; message: string };

/**
 * Renders Mermaid source to inline SVG (sanitised by Mermaid's strict mode).
 * Syntax or load errors never break the view: the source is shown instead.
 */
export function MermaidView({ source }: { source: string }) {
  const [state, setState] = useState<RenderState>({ status: "rendering" });

  useEffect(() => {
    let cancelled = false;
    setState({ status: "rendering" });
    renderMermaid(source).then(
      (svg) => {
        if (!cancelled) setState({ status: "ready", svg });
      },
      (err: unknown) => {
        if (!cancelled) setState({ status: "error", message: errorMessage(err) });
      },
    );
    return () => {
      cancelled = true;
    };
  }, [source]);

  if (state.status === "rendering") return <Loading text="Rendering diagram…" compact />;

  if (state.status === "error") {
    return (
      <div className="diagram-error">
        <Callout tone="warn" title="Diagram could not be rendered — showing source">
          {state.message}
        </Callout>
        <pre className="source-block">{source}</pre>
      </div>
    );
  }

  return <div className="mermaid-view" dangerouslySetInnerHTML={{ __html: state.svg }} />;
}
