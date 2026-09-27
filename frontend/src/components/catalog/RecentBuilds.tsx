import type { JobSummary } from "../../api/types";
import { routes } from "../../hooks/useHashRoute";
import { useNow } from "../../hooks/useNow";
import type { Resource } from "../../hooks/useResource";
import { formatRelative, formatTooltipTime, parseTime } from "../../lib/format";
import { doneCount } from "../../lib/status";
import { Callout } from "../Callout";
import { Panel } from "../Panel";
import { ProgressBar } from "../ProgressBar";
import { EmptyState, Loading } from "../States";
import { JobStatusChip } from "../Status";

const LIMIT = 8;

export function RecentBuilds({ jobs }: { jobs: Resource<JobSummary[]> }) {
  const now = useNow(30_000);
  const list = jobs.data?.slice(0, LIMIT) ?? [];

  return (
    <Panel
      title="Recent builds"
      meta={
        <a className="panel__link" href={routes.builds}>
          All builds ▸
        </a>
      }
    >
      {jobs.loading ? (
        <Loading text="Loading builds…" compact />
      ) : !jobs.data ? (
        <div className="panel__body">
          <Callout
            tone="danger"
            title="Builds unavailable"
            actions={
              <button type="button" className="btn btn--sm" onClick={jobs.reload}>
                Retry
              </button>
            }
          >
            {jobs.error}
          </Callout>
        </div>
      ) : list.length === 0 ? (
        <EmptyState compact text="No builds yet" hint="Pick a blueprint or write a brief to start one." />
      ) : (
        <ul className="recent-list">
          {list.map((job) => {
            const created = parseTime(job.created_at);
            return (
              <li key={job.id}>
                <a className="recent-item" href={routes.job(job.id)}>
                  <span className="recent-item__top">
                    <span className="recent-item__title" title={job.title}>
                      {job.title}
                    </span>
                    {created != null && (
                      <time
                        className="recent-item__time"
                        dateTime={job.created_at}
                        title={formatTooltipTime(created)}
                      >
                        {formatRelative(created, now)}
                      </time>
                    )}
                  </span>
                  <span className="recent-item__bottom">
                    <JobStatusChip status={job.status} small />
                    <span className="recent-item__bar" aria-hidden="true">
                      <ProgressBar progress={job.progress} size="sm" />
                    </span>
                    <span className="recent-item__progress">
                      {doneCount(job.progress)}/{job.progress.total}
                      <span className="sr-only"> tasks finished</span>
                    </span>
                  </span>
                </a>
              </li>
            );
          })}
        </ul>
      )}
    </Panel>
  );
}
