import { useCallback, useEffect, useMemo, useState } from "react";

import { fileUrl } from "../../api/client";
import type { Artifact } from "../../api/types";
import { useFileText } from "../../hooks/useFileText";
import { basename, extension, formatBytes } from "../../lib/format";
import { highlightCode, languageLabel } from "../../lib/highlight";
import { ancestorDirs, buildFileTree } from "../../lib/trees";
import { Callout } from "../Callout";
import { EmptyState, Loading } from "../States";
import { FileTree } from "./FileTree";

const TEXT_TYPES = new Set([
  "application/json",
  "application/xml",
  "application/toml",
  "application/yaml",
  "application/x-yaml",
  "application/javascript",
  "image/svg+xml",
]);
const TEXT_EXTENSIONS = new Set(["py", "pyi", "json", "toml", "ini", "cfg", "md", "yaml", "yml", "svg", "xml", "mmd", "txt"]);

function isTextual(artifact: Artifact): boolean {
  const type = artifact.media_type.split(";")[0]?.trim().toLowerCase() ?? "";
  return (
    type.startsWith("text/") ||
    TEXT_TYPES.has(type) ||
    type.endsWith("+json") ||
    type.endsWith("+xml") ||
    TEXT_EXTENSIONS.has(extension(artifact.path))
  );
}

/** README.md (shallowest wins) if present, else the first source file, else the first file. */
export function defaultFilePath(artifacts: Artifact[]): string | null {
  const readmes = artifacts
    .filter((a) => basename(a.path).toLowerCase() === "readme.md")
    .sort((a, b) => a.path.split("/").length - b.path.split("/").length);
  const pick = readmes[0] ?? artifacts.find((a) => a.kind === "source") ?? artifacts[0];
  return pick?.path ?? null;
}

/** Gutter text ("1\n2\n…") and line count; a trailing newline does not start a new line. */
function lineNumbers(text: string): { gutter: string; count: number } {
  let count = 1;
  for (let i = 0; i < text.length; i += 1) if (text.charCodeAt(i) === 10) count += 1;
  if (count > 1 && text.endsWith("\n")) count -= 1;
  return { gutter: Array.from({ length: count }, (_, i) => String(i + 1)).join("\n"), count };
}

function CodeViewer({ jobId, artifact }: { jobId: string; artifact: Artifact }) {
  const textual = isTextual(artifact);
  const file = useFileText(jobId, textual ? artifact : null);
  const text = file.status === "ready" ? file.text : null;
  const html = useMemo(() => (text == null ? "" : highlightCode(text, artifact.path)), [text, artifact.path]);
  const numbering = useMemo(() => (text == null ? null : lineNumbers(text)), [text]);
  const lines = numbering?.count ?? null;

  let body;
  if (!textual) {
    body = <EmptyState text="Binary file" hint="Download the file to inspect it." />;
  } else if (file.status === "ready") {
    body = (
      <div className="code-viewer__body" tabIndex={0} aria-label={`Contents of ${artifact.path}`}>
        <pre className="code-gutter" aria-hidden="true">
          {numbering?.gutter}
        </pre>
        <pre className="code-content">
          <code className="hljs" dangerouslySetInnerHTML={{ __html: html }} />
        </pre>
      </div>
    );
  } else if (file.status === "error") {
    body = (
      <div className="panel__body code-viewer__state">
        <Callout
          tone="danger"
          title="Could not load file"
          actions={
            <button type="button" className="btn btn--sm" onClick={file.retry}>
              Retry
            </button>
          }
        >
          {file.message}
        </Callout>
      </div>
    );
  } else {
    body = <Loading text="Loading file…" />;
  }

  return (
    <section className="code-viewer" aria-label={`File ${artifact.path}`}>
      <header className="code-viewer__head">
        <span className="code-viewer__path" title={artifact.path}>
          {artifact.path}
        </span>
        <span className="code-viewer__meta">
          {languageLabel(artifact.path)} · {formatBytes(artifact.size)}
          {lines != null && ` · ${lines} ${lines === 1 ? "line" : "lines"}`}
        </span>
        <a
          className="btn btn--sm btn--ghost"
          href={fileUrl(jobId, artifact.path)}
          download={basename(artifact.path)}
        >
          Download file
        </a>
      </header>
      {body}
    </section>
  );
}

interface Props {
  jobId: string;
  artifacts: Artifact[];
  /** Explicit selection (null = default file). */
  selectedPath: string | null;
  onSelect: (path: string) => void;
}

/** File explorer + syntax-highlighted viewer for the generated project. */
export function CodeTab({ jobId, artifacts, selectedPath, onSelect }: Props) {
  const tree = useMemo(() => buildFileTree(artifacts), [artifacts]);
  const byPath = useMemo(() => new Map(artifacts.map((a) => [a.path, a])), [artifacts]);
  const activePath =
    selectedPath && byPath.has(selectedPath) ? selectedPath : defaultFilePath(artifacts);
  const active = activePath ? byPath.get(activePath) : undefined;
  const [collapsed, setCollapsed] = useState<ReadonlySet<string>>(() => new Set());

  // Make sure the selected file is visible (its folders expanded).
  useEffect(() => {
    if (!activePath) return;
    const ancestors = ancestorDirs(activePath);
    setCollapsed((prev) =>
      ancestors.some((dir) => prev.has(dir))
        ? new Set([...prev].filter((dir) => !ancestors.includes(dir)))
        : prev,
    );
  }, [activePath]);

  const toggle = useCallback((dir: string) => {
    setCollapsed((prev) => {
      const next = new Set(prev);
      if (next.has(dir)) next.delete(dir);
      else next.add(dir);
      return next;
    });
  }, []);

  if (artifacts.length === 0) {
    return (
      <EmptyState text="Awaiting output…" hint="Generated files appear here as the agents produce them." />
    );
  }

  return (
    <div className="code-layout">
      <FileTree
        root={tree}
        activePath={activePath}
        collapsed={collapsed}
        onToggle={toggle}
        onSelect={onSelect}
      />
      {active ? (
        <CodeViewer key={active.path} jobId={jobId} artifact={active} />
      ) : (
        <EmptyState text="Select a file" />
      )}
    </div>
  );
}
