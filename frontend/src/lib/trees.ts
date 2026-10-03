// Tree builders: the agent task hierarchy and the generated project's file tree.

import type { Artifact, TaskRecord } from "../api/types";
import { parseTime } from "./format";

// ---------------------------------------------------------------------------
// Task tree (flattened for rendering with connector guides)
// ---------------------------------------------------------------------------

/** How to draw one indentation column to the left of a task row. */
export type Guide = "blank" | "line" | "tee" | "elbow";

export interface TaskRow {
  task: TaskRecord;
  depth: number;
  /** One entry per ancestor level: continuation lines and this row's own connector. */
  guides: Guide[];
  hasChildren: boolean;
}

/**
 * Orders tasks into a parent/child tree (via `parent_id`) and flattens it
 * depth-first. Siblings keep creation order. Tasks whose parent is unknown are
 * treated as roots, and a visited set guards against malformed cycles.
 */
export function flattenTaskTree(tasks: TaskRecord[]): TaskRow[] {
  const order = new Map<string, number>();
  tasks.forEach((task, index) => order.set(task.id, index));
  const created = (task: TaskRecord): number => parseTime(task.created_at) ?? 0;
  const sorted = [...tasks].sort(
    (a, b) => created(a) - created(b) || (order.get(a.id) ?? 0) - (order.get(b.id) ?? 0),
  );

  const byId = new Map(sorted.map((task) => [task.id, task]));
  const children = new Map<string, TaskRecord[]>();
  const roots: TaskRecord[] = [];
  for (const task of sorted) {
    const parentId = task.parent_id;
    if (parentId && parentId !== task.id && byId.has(parentId)) {
      const list = children.get(parentId) ?? [];
      list.push(task);
      children.set(parentId, list);
    } else {
      roots.push(task);
    }
  }

  const rows: TaskRow[] = [];
  const visited = new Set<string>();

  const visit = (task: TaskRecord, depth: number, ancestors: Guide[], isLast: boolean): void => {
    if (visited.has(task.id)) return;
    visited.add(task.id);
    const kids = (children.get(task.id) ?? []).filter((child) => !visited.has(child.id));
    const guides: Guide[] = depth === 0 ? [] : [...ancestors, isLast ? "elbow" : "tee"];
    rows.push({ task, depth, guides, hasChildren: kids.length > 0 });
    // Children of this task continue this level's line only if more siblings follow.
    const nextAncestors: Guide[] = depth === 0 ? [] : [...ancestors, isLast ? "blank" : "line"];
    kids.forEach((child, index) => visit(child, depth + 1, nextAncestors, index === kids.length - 1));
  };

  roots.forEach((root, index) => visit(root, 0, [], index === roots.length - 1));
  // Anything unreachable (cyclic parent links) is still shown, at the root level.
  for (const task of sorted) visit(task, 0, [], true);
  return rows;
}

// ---------------------------------------------------------------------------
// File tree
// ---------------------------------------------------------------------------

export interface FileNode {
  type: "file";
  name: string;
  path: string;
  artifact: Artifact;
}

export interface DirNode {
  type: "dir";
  name: string;
  path: string;
  dirs: DirNode[];
  files: FileNode[];
}

const collator = new Intl.Collator("en", { numeric: true, sensitivity: "base" });

/** Builds a folders-first, alphabetically sorted tree from artifact paths. */
export function buildFileTree(artifacts: Artifact[]): DirNode {
  const root: DirNode = { type: "dir", name: "", path: "", dirs: [], files: [] };
  const dirIndex = new Map<string, DirNode>([["", root]]);

  for (const artifact of artifacts) {
    const parts = artifact.path.split("/").filter(Boolean);
    const fileName = parts.pop();
    if (!fileName) continue;
    let parent = root;
    for (const part of parts) {
      const path = parent.path ? `${parent.path}/${part}` : part;
      let dir = dirIndex.get(path);
      if (!dir) {
        dir = { type: "dir", name: part, path, dirs: [], files: [] };
        dirIndex.set(path, dir);
        parent.dirs.push(dir);
      }
      parent = dir;
    }
    if (!parent.files.some((file) => file.path === artifact.path)) {
      parent.files.push({ type: "file", name: fileName, path: artifact.path, artifact });
    }
  }

  const sortDir = (dir: DirNode): void => {
    dir.dirs.sort((a, b) => collator.compare(a.name, b.name));
    dir.files.sort((a, b) => collator.compare(a.name, b.name));
    dir.dirs.forEach(sortDir);
  };
  sortDir(root);
  return root;
}

/** Folder paths that contain `filePath` ("a", "a/b" for "a/b/c.py"). */
export function ancestorDirs(filePath: string): string[] {
  const parts = filePath.split("/").filter(Boolean);
  parts.pop();
  return parts.map((_, index) => parts.slice(0, index + 1).join("/"));
}
