import { useCallback, useId, useMemo, useState, type ReactNode } from "react";

import type { JobEvent, JobRecord } from "../api/types";
import { Callout } from "../components/Callout";
import { CodeTab } from "../components/job/CodeTab";
import { CommsLog, StreamIndicator } from "../components/job/CommsLog";
import { DiagramsTab } from "../components/job/DiagramsTab";
import { checkCounts, InspectionTab } from "../components/job/InspectionTab";
import { JobHeader } from "../components/job/JobHeader";
import { ModulesTab } from "../components/job/ModulesTab";
import { TaskTree } from "../components/job/TaskTree";
import { Panel } from "../components/Panel";
import { EmptyState, Loading } from "../components/States";
import { tabId, tabPanelId, Tabs, type TabItem } from "../components/Tabs";
import { useDocumentTitle } from "../hooks/useDocumentTitle";
import { routes } from "../hooks/useHashRoute";
import { useJob, type JobFeed, type StreamState } from "../hooks/useJob";
import { doneCount } from "../lib/status";

type TabKey = "diagrams" | "code" | "modules" | "inspection";
const TAB_KEYS: TabKey[] = ["diagrams", "code", "modules", "inspection"];

export function JobView({ jobId }: { jobId: string }) {
  const feed = useJob(jobId);
  const { job, error, refresh } = feed;
  useDocumentTitle(job ? job.title : "Build");

  if (job) return <JobConsole job={job} events={feed.events} stream={feed.stream} error={error} />;

  if (error?.status === 404) {
    return (
      <EmptyState text="Build not found" hint={<>No build with id <span className="mono">{jobId}</span>.</>}>
        <a className="btn" href={routes.builds}>
          All builds
        </a>
      </EmptyState>
    );
  }
  if (error) {
    return (
      <Callout
        tone="danger"
        title="Could not load build"
        actions={
          <button type="button" className="btn btn--sm" onClick={refresh}>
            Retry
          </button>
        }
      >
        {error.message}
      </Callout>
    );
  }
  return <Loading text="Opening build…" />;
}

interface ConsoleProps {
  job: JobRecord;
  events: JobEvent[];
  stream: StreamState;
  error: JobFeed["error"];
}

function JobConsole({ job, events, stream, error }: ConsoleProps) {
  const idBase = useId();
  const [tab, setTab] = useState<TabKey>("diagrams");
  // Panels mount on first visit and then stay mounted (hidden) to keep their state.
  const [visited, setVisited] = useState<ReadonlySet<TabKey>>(() => new Set<TabKey>(["diagrams"]));
  const [selectedPath, setSelectedPath] = useState<string | null>(null);

  const openTab = useCallback((key: TabKey) => {
    setTab(key);
    setVisited((prev) => (prev.has(key) ? prev : new Set(prev).add(key)));
  }, []);

  const viewCode = useCallback(
    (path: string) => {
      setSelectedPath(path);
      openTab("code");
    },
    [openTab],
  );

  const diagrams = useMemo(() => job.artifacts.filter((a) => a.kind === "diagram"), [job.artifacts]);
  const inspectionCounts = job.inspection ? checkCounts(job.inspection) : null;

  const tabs: TabItem<TabKey>[] = [
    { id: "diagrams", label: "Diagrams", count: diagrams.length },
    { id: "code", label: "Code", count: job.artifacts.length },
    { id: "modules", label: "Modules", count: job.modules.length },
    {
      id: "inspection",
      label: "Inspection",
      count: job.inspection ? job.inspection.checks.length : null,
      tone: inspectionCounts?.fail ? "danger" : inspectionCounts?.warn ? "warn" : null,
    },
  ];

  const renderTab = (key: TabKey): ReactNode => {
    switch (key) {
      case "diagrams":
        return <DiagramsTab jobId={job.id} diagrams={diagrams} />;
      case "code":
        return (
          <CodeTab
            jobId={job.id}
            artifacts={job.artifacts}
            selectedPath={selectedPath}
            onSelect={setSelectedPath}
          />
        );
      case "modules":
        return <ModulesTab job={job} onViewCode={viewCode} />;
      case "inspection":
        return <InspectionTab inspection={job.inspection} />;
    }
  };

  return (
    <div className="job">
      <JobHeader job={job} />

      {job.status === "failed" && (
        <Callout tone="danger" title="Build failed" className="job-alert">
          {job.error || "The factory reported a failure without details."}
        </Callout>
      )}
      {error && (
        <Callout tone="warn" title="Live updates interrupted" className="job-alert">
          {error.message} Showing the last known state; retrying automatically.
        </Callout>
      )}

      <div className="job-grid">
        <div className="job-col">
          <Panel
            title="Assembly line"
            meta={
              <span className="num">
                {doneCount(job.progress)}/{job.progress.total} tasks
              </span>
            }
          >
            <TaskTree tasks={job.tasks} />
          </Panel>
          <Panel title="Comms log" meta={<StreamIndicator state={stream} count={events.length} />}>
            <CommsLog events={events} tasks={job.tasks} live={stream === "live"} />
          </Panel>
        </div>

        <section className="panel output" aria-label="Build output">
          <Tabs label="Build output" idBase={idBase} items={tabs} active={tab} onChange={openTab} />
          {TAB_KEYS.map((key) => (
            <div
              key={key}
              role="tabpanel"
              id={tabPanelId(idBase, key)}
              aria-labelledby={tabId(idBase, key)}
              hidden={tab !== key}
              tabIndex={0}
              className="tabpanel"
            >
              {visited.has(key) && renderTab(key)}
            </div>
          ))}
        </section>
      </div>
    </div>
  );
}
