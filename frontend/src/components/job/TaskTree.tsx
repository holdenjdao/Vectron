import { memo, useMemo } from "react";

import type { TaskRecord } from "../../api/types";
import { useNow } from "../../hooks/useNow";
import { cx } from "../../lib/cx";
import { formatDuration, parseTime } from "../../lib/format";
import { roleKey } from "../../lib/status";
import { flattenTaskTree, type TaskRow } from "../../lib/trees";
import { EmptyState } from "../States";
import { TaskStatusIcon } from "../Status";

function LiveDuration({ since }: { since: number }) {
  const now = useNow(250);
  return (
    <span className="task-row__duration task-row__duration--live">{formatDuration(now - since)}</span>
  );
}

function TaskDuration({ task }: { task: TaskRecord }) {
  if (task.duration_ms != null) {
    return <span className="task-row__duration">{formatDuration(task.duration_ms)}</span>;
  }
  const started = parseTime(task.started_at);
  if (task.status === "running" && started != null) return <LiveDuration since={started} />;
  return null;
}

/** Task records get new identities on every refetch; compare what a row actually shows. */
function sameRow(prev: { row: TaskRow }, next: { row: TaskRow }): boolean {
  const a = prev.row;
  const b = next.row;
  return (
    a.depth === b.depth &&
    a.hasChildren === b.hasChildren &&
    a.guides.join() === b.guides.join() &&
    a.task.status === b.task.status &&
    a.task.agent === b.task.agent &&
    a.task.role === b.task.role &&
    a.task.title === b.task.title &&
    a.task.summary === b.task.summary &&
    a.task.error === b.task.error &&
    a.task.duration_ms === b.task.duration_ms &&
    a.task.started_at === b.task.started_at
  );
}

const TaskRowView = memo(function TaskRowView({ row }: { row: TaskRow }) {
  const { task } = row;
  return (
    <li className={cx("task-row", `task-row--${task.status}`)}>
      <span className="task-row__guides" aria-hidden="true">
        {row.guides.map((guide, index) => (
          <span key={index} className={`guide guide--${guide}`} />
        ))}
      </span>
      <span className={cx("task-row__node", row.hasChildren && "task-row__node--parent")}>
        <TaskStatusIcon status={task.status} />
      </span>
      <div className="task-row__main">
        <div className="task-row__line">
          {row.depth > 0 && <span className="sr-only">Level {row.depth + 1}: </span>}
          <span className="agent-name task-row__agent" data-role={roleKey(task.role)}>
            {task.agent}
          </span>
          <span className="task-row__title" title={task.title}>
            {task.title}
          </span>
          <TaskDuration task={task} />
        </div>
        {task.summary && (
          <div className="task-row__summary" title={task.summary}>
            {task.summary}
          </div>
        )}
        {task.status === "failed" && task.error && <div className="task-row__error">{task.error}</div>}
      </div>
    </li>
  );
}, sameRow);

/** Agent task hierarchy with connector lines, in creation order. */
export function TaskTree({ tasks }: { tasks: TaskRecord[] }) {
  const rows = useMemo(() => flattenTaskTree(tasks), [tasks]);
  if (rows.length === 0) {
    return <EmptyState compact text="Awaiting orders…" hint="The Commander is reading the request." />;
  }
  return (
    <ol className="task-tree" aria-label="Agent tasks">
      {rows.map((row) => (
        <TaskRowView key={row.task.id} row={row} />
      ))}
    </ol>
  );
}
