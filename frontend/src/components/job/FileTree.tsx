import { useEffect, useRef, type CSSProperties } from "react";

import type { ArtifactKind } from "../../api/types";
import type { DirNode, FileNode } from "../../lib/trees";

interface TreeProps {
  root: DirNode;
  activePath: string | null;
  collapsed: ReadonlySet<string>;
  onToggle: (dirPath: string) => void;
  onSelect: (filePath: string) => void;
}

const depthStyle = (depth: number) => ({ "--depth": depth }) as CSSProperties;

function FolderIcon({ open }: { open: boolean }) {
  return (
    <svg className="tree-item__icon" width="14" height="12" viewBox="0 0 14 12" aria-hidden="true">
      <path
        d={open ? "M1 2.5 H5.2 L6.4 3.8 H13 V10.5 H1 Z" : "M1 1.5 H5.2 L6.4 2.8 H13 V10.5 H1 Z"}
        fill={open ? "rgba(125,175,215,0.12)" : "none"}
        stroke="currentColor"
        strokeWidth="1.1"
        strokeLinejoin="round"
        opacity="0.8"
      />
    </svg>
  );
}

function FileIcon({ kind }: { kind: ArtifactKind }) {
  return (
    <svg
      className={`tree-item__icon kind-${kind}`}
      width="12"
      height="14"
      viewBox="0 0 12 14"
      aria-hidden="true"
    >
      <path
        d="M1.5 1 H7.5 L10.5 4 V13 H1.5 Z M7.5 1 V4 H10.5"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.1"
        strokeLinejoin="round"
      />
    </svg>
  );
}

function FileItem({
  file,
  depth,
  active,
  onSelect,
}: {
  file: FileNode;
  depth: number;
  active: boolean;
  onSelect: (path: string) => void;
}) {
  const ref = useRef<HTMLButtonElement>(null);
  // Bring the selection into view, e.g. when it was chosen from the Modules tab.
  useEffect(() => {
    if (active) ref.current?.scrollIntoView({ block: "nearest" });
  }, [active]);
  return (
    <button
      ref={ref}
      type="button"
      className="tree-item tree-item--file"
      style={depthStyle(depth)}
      aria-current={active ? "true" : undefined}
      title={file.path}
      onClick={() => onSelect(file.path)}
    >
      <FileIcon kind={file.artifact.kind} />
      <span className="tree-item__name">{file.name}</span>
    </button>
  );
}

function DirContents({ dir, depth, ...props }: TreeProps & { dir: DirNode; depth: number }) {
  const { activePath, collapsed, onToggle, onSelect } = props;
  return (
    <ul>
      {dir.dirs.map((sub) => {
        const open = !collapsed.has(sub.path);
        return (
          <li key={sub.path}>
            <button
              type="button"
              className="tree-item tree-item--dir"
              style={depthStyle(depth)}
              aria-expanded={open}
              title={sub.path}
              onClick={() => onToggle(sub.path)}
            >
              <span className="tree-item__chevron" aria-hidden="true">
                ▸
              </span>
              <FolderIcon open={open} />
              <span className="tree-item__name">{sub.name}</span>
            </button>
            {open && <DirContents {...props} dir={sub} depth={depth + 1} />}
          </li>
        );
      })}
      {dir.files.map((file) => (
        <li key={file.path}>
          <FileItem file={file} depth={depth} active={file.path === activePath} onSelect={onSelect} />
        </li>
      ))}
    </ul>
  );
}

/** Explorer for every generated file; folders first, collapsible. */
export function FileTree(props: TreeProps) {
  return (
    <nav className="file-tree" aria-label="Generated files">
      <DirContents {...props} dir={props.root} depth={0} />
    </nav>
  );
}
