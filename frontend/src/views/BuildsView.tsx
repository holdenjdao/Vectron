import { Callout } from "../components/Callout";
import { Panel } from "../components/Panel";
import { ProgressBar } from "../components/ProgressBar";
import { EmptyState, Loading } from "../components/States";
import { JobStatusChip } from "../components/Status";
import { useDocumentTitle } from "../hooks/useDocumentTitle";
import { routes } from "../hooks/useHashRoute";
import { useJobsList } from "../hooks/useJobsList";
import { useNow } from "../hooks/useNow";
import { formatDateTime, formatRelative, formatTooltipTime, parseTime } from "../lib/format";
import { doneCount, isJobActive } from "../lib/status";

export function BuildsView() {
  useDocumentTitle("Builds");
  const jobs = useJobsList();
  const now = useNow(30_000);
  const list = jobs.data ?? [];
  const active = list.filter((job) => isJobActive(job.status)).length;

  let content;
  if (jobs.loading) {
    content = <Loading text="Loading builds…" />;
  } else if (!jobs.data) {
    content = (
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
    );
  } else if (list.length === 0) {
    content = (
      <EmptyState text="No builds yet" hint="Start one from the catalog.">
        <a className="btn btn--primary" href={routes.catalog}>
          Open catalog
        </a>
      </EmptyState>
    );
  } else {
    content = (
      <div className="table-wrap">
        <table className="table builds-table">
          <caption className="sr-only">All builds, newest first</caption>
          <thead>
            <tr>
              <th scope="col">Status</th>
              <th scope="col">Build</th>
              <th scope="col">Blueprint</th>
              <th scope="col">Created</th>
              <th scope="col">Progress</th>
              <th scope="col">
                <span className="sr-only">Open</span>
              </th>
            </tr>
          </thead>
          <tbody>
            {list.map((job) => {
              const created = parseTime(job.created_at);
              const done = doneCount(job.progress);
              return (
                <tr key={job.id}>
                  <td>
                    <JobStatusChip status={job.status} small />
                  </td>
                  <td>
                    <a className="builds-table__title" href={routes.job(job.id)}>
                      {job.title}
                    </a>
                    <span className="builds-table__id">{job.id}</span>
                  </td>
                  <td className="mono dim">{job.blueprint_id ?? "— brief —"}</td>
                  <td className="mono dim">
                    {created != null ? (
                      <time dateTime={job.created_at} title={formatTooltipTime(created)}>
                        {formatDateTime(created)}
                        <span className="builds-table__id">{formatRelative(created, now)}</span>
                      </time>
                    ) : (
                      "—"
                    )}
                  </td>
                  <td>
                    <div className="progress-cell">
                      <ProgressBar progress={job.progress} size="sm" />
                      <span className="progress-cell__text">
                        {done}/{job.progress.total}
                      </span>
                    </div>
                  </td>
                  <td>
                    <a
                      className="btn btn--sm btn--ghost"
                      href={routes.job(job.id)}
                      aria-label={`Open build ${job.title}`}
                    >
                      Open ▸
                    </a>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    );
  }

  return (
    <div className="builds">
      <header className="page-head">
        <div>
          <p className="eyebrow">Build registry</p>
          <h1 className="page-title">Builds</h1>
        </div>
        <div className="page-head__actions">
          <button type="button" className="btn" onClick={jobs.reload}>
            Refresh
          </button>
          <a className="btn btn--primary" href={routes.catalog}>
            New build
          </a>
        </div>
      </header>
      <Panel
        title="All builds"
        meta={
          jobs.data ? (
            <span>
              {list.length} total{active > 0 ? ` · ${active} active` : ""}
            </span>
          ) : null
        }
      >
        {content}
      </Panel>
    </div>
  );
}
