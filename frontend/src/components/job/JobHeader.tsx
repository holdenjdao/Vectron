import type { ReactNode } from "react";

import { bundleUrl } from "../../api/client";
import type { JobRecord } from "../../api/types";
import { routes } from "../../hooks/useHashRoute";
import { useNow } from "../../hooks/useNow";
import { cx } from "../../lib/cx";
import { formatBytes, formatCompact, formatElapsed, formatNumber, parseTime } from "../../lib/format";
import { doneCount, isJobTerminal, JOB_STATUS_LABEL } from "../../lib/status";
import { ProgressBar } from "../ProgressBar";
import { JobStatusChip } from "../Status";

function ReadoutCell({
  label,
  children,
  grow = false,
  title,
}: {
  label: string;
  children: ReactNode;
  grow?: boolean;
  title?: string;
}) {
  return (
    <div className={cx("readout__cell", grow && "readout__cell--grow")} title={title}>
      <dt className="readout__label">{label}</dt>
      <dd className="readout__value">{children}</dd>
    </div>
  );
}

/** Stopwatch that ticks while the job is running and freezes when it ends. */
function Elapsed({ job }: { job: JobRecord }) {
  const start = parseTime(job.started_at) ?? parseTime(job.created_at);
  const end = parseTime(job.finished_at);
  const live = !isJobTerminal(job.status) && end == null;
  const now = useNow(100, live);
  if (start == null) return <>—</>;
  return <span className="num">{formatElapsed((end ?? now) - start)}</span>;
}

function BundleButton({ job }: { job: JobRecord }) {
  const { bundle } = job;
  if (!bundle) {
    const reason =
      job.status === "failed"
        ? "No bundle: the build failed before packaging."
        : "Available once the Quartermaster has packaged the build.";
    return (
      <button type="button" className="btn btn--primary" disabled title={reason}>
        Download bundle (.zip)
      </button>
    );
  }
  return (
    <a
      className="btn btn--primary"
      href={bundleUrl(job.id)}
      download={bundle.filename}
      title={`${bundle.filename} · ${bundle.file_count} files · sha256 ${bundle.sha256}`}
    >
      Download bundle (.zip)
      <span className="btn__meta">{formatBytes(bundle.size)}</span>
    </a>
  );
}

function engineLabel(job: JobRecord): string {
  if (job.llm.provider === "anthropic") return `Claude · ${job.llm.model ?? "default"}`;
  if (job.llm.provider === "offline") return "Offline";
  return job.llm.provider || "—";
}

export function JobHeader({ job }: { job: JobRecord }) {
  const done = doneCount(job.progress);
  const { calls, input_tokens, output_tokens } = job.usage;
  const tokens = input_tokens + output_tokens;
  const brief = job.request.brief?.trim();

  return (
    <header className="job-head">
      <div className="job-head__top">
        <div className="job-head__titles">
          <nav className="crumbs" aria-label="Breadcrumb">
            <a href={routes.builds}>Builds</a>
            <span className="crumbs__sep" aria-hidden="true">
              /
            </span>
            <span className="crumbs__current" aria-current="page">
              {job.blueprint_id ?? "Brief build"}
            </span>
          </nav>
          <h1 className="job-title">{job.title}</h1>
          {brief && (
            <p className="job-brief">
              <span className="vx-label job-brief__label">Brief</span>
              <span className="job-brief__text" title={brief}>
                {brief}
              </span>
            </p>
          )}
        </div>
        <div className="job-actions">
          <BundleButton job={job} />
          <a className="btn" href={routes.catalog}>
            New build
          </a>
        </div>
      </div>

      <dl className="readout">
        <ReadoutCell label="Status">
          <JobStatusChip status={job.status} />
        </ReadoutCell>
        <ReadoutCell label="Job ID">
          <span className="readout__value--id" title={job.id}>
            {job.id}
          </span>
        </ReadoutCell>
        <ReadoutCell label="Elapsed">
          <Elapsed job={job} />
        </ReadoutCell>
        <ReadoutCell label="Engine">{engineLabel(job)}</ReadoutCell>
        {calls > 0 && (
          <ReadoutCell
            label="LLM usage"
            title={`${formatNumber(input_tokens)} input + ${formatNumber(output_tokens)} output tokens`}
          >
            {calls} LLM {calls === 1 ? "call" : "calls"} · {formatCompact(tokens)} tokens
          </ReadoutCell>
        )}
        <ReadoutCell label="Assembly progress" grow>
          <span className="readout__progress">
            <ProgressBar progress={job.progress} />
            <span className="num">
              {done}/{job.progress.total}
            </span>
          </span>
        </ReadoutCell>
      </dl>

      {/* Announces status transitions (the initial value is not read out). */}
      <p className="sr-only" aria-live="polite">
        Build {JOB_STATUS_LABEL[job.status]?.toLowerCase() ?? job.status}
      </p>
    </header>
  );
}
