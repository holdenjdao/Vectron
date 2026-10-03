import { useLayoutEffect, useMemo, useRef, useState } from "react";

import type { JobEvent, TaskRecord } from "../../api/types";
import type { StreamState } from "../../hooks/useJob";
import { cx } from "../../lib/cx";
import { formatClock, formatTooltipTime, parseTime } from "../../lib/format";
import { roleKey } from "../../lib/status";
import { Glyph } from "../Status";

/** Distance from the bottom (px) within which the log keeps following new lines. */
const STICKY_THRESHOLD = 24;

function eventTone(type: string): string {
  if (type.endsWith(".failed")) return "failed";
  if (type.endsWith(".succeeded")) return "succeeded";
  if (type.startsWith("artifact.")) return "artifact";
  if (type === "task.log") return "log";
  return "default";
}

/** Agent label for an event: the task's agent, or FACTORY for job-level events. */
function speaker(event: JobEvent, tasks: Map<string, TaskRecord>): { name: string; role: string } {
  if (!event.task_id) return { name: "Factory", role: "factory" };
  const task = tasks.get(event.task_id);
  if (task) return { name: task.agent, role: roleKey(task.role) };
  // The task may not be in the latest snapshot yet; fall back to what the event says.
  const agent = event.data["agent"];
  return { name: typeof agent === "string" && agent ? agent : "Agent", role: "unknown" };
}

interface Props {
  events: JobEvent[];
  tasks: TaskRecord[];
  live: boolean;
}

/** Scrolling console of job events: `HH:MM:SS.mmm  AGENT  message`. */
export function CommsLog({ events, tasks, live }: Props) {
  const taskById = useMemo(() => new Map(tasks.map((task) => [task.id, task])), [tasks]);
  const scrollRef = useRef<HTMLDivElement>(null);
  const followRef = useRef(true);
  const [showJump, setShowJump] = useState(false);

  // Follow new output unless the operator has scrolled up to read.
  useLayoutEffect(() => {
    const el = scrollRef.current;
    if (!el) return;
    if (followRef.current) el.scrollTop = el.scrollHeight;
    else if (events.length > 0) setShowJump(true);
  }, [events.length]);

  const onScroll = () => {
    const el = scrollRef.current;
    if (!el) return;
    const atBottom = el.scrollHeight - el.scrollTop - el.clientHeight <= STICKY_THRESHOLD;
    followRef.current = atBottom;
    if (atBottom) setShowJump(false);
  };

  const jumpToLatest = () => {
    const el = scrollRef.current;
    if (!el) return;
    followRef.current = true;
    el.scrollTop = el.scrollHeight;
    setShowJump(false);
  };

  return (
    <div className="comms-wrap">
      <div
        ref={scrollRef}
        className="comms"
        role="log"
        aria-live="off"
        aria-label="Comms log"
        tabIndex={0}
        onScroll={onScroll}
      >
        {events.length === 0 && <div className="comms__empty">Waiting for transmissions…</div>}
        {events.map((event) => {
          const who = speaker(event, taskById);
          const ms = parseTime(event.ts);
          return (
            <div
              key={event.seq}
              className={cx("comms__line", `comms__line--${eventTone(event.type)}`)}
              title={`#${event.seq} · ${event.type}`}
            >
              <time
                className="comms__time"
                dateTime={event.ts || undefined}
                title={ms != null ? formatTooltipTime(ms) : undefined}
              >
                {ms != null ? formatClock(ms) : "--:--:--.---"}
              </time>
              <span className="comms__agent" data-role={who.role} title={who.name}>
                {who.name}
              </span>
              <span className="comms__msg">{event.message || event.type}</span>
            </div>
          );
        })}
        {live && (
          <div className="comms__line" aria-hidden="true">
            <span />
            <span />
            <span>
              <span className="comms__cursor" />
            </span>
          </div>
        )}
      </div>
      {showJump && (
        <button type="button" className="btn btn--sm comms__jump" onClick={jumpToLatest}>
          <Glyph kind="pulse" size={10} /> Jump to latest
        </button>
      )}
    </div>
  );
}

const STREAM_LABEL: Record<StreamState, string> = {
  connecting: "Connecting",
  live: "Live",
  reconnecting: "Reconnecting",
  ended: "Stream closed",
  unavailable: "Stream unavailable",
};

/** Header readout for the comms log: stream state and event count. */
export function StreamIndicator({ state, count }: { state: StreamState; count: number }) {
  return (
    <>
      <span className={cx("stream-state", `stream-state--${state}`)}>
        {state === "live" && <Glyph kind="pulse" size={10} />}
        {STREAM_LABEL[state]}
      </span>
      <span className="num">{count} events</span>
    </>
  );
}
