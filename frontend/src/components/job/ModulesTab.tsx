import { useMemo } from "react";

import { moduleBundleUrl } from "../../api/client";
import type { JobRecord, ModuleBuild } from "../../api/types";
import { isJobTerminal } from "../../lib/status";
import { EmptyState } from "../States";

type ProvenanceKind = "part" | "stub" | "llm" | "other";

function provenanceKind(provenance: string): ProvenanceKind {
  if (provenance.startsWith("part:")) return "part";
  if (provenance === "stub") return "stub";
  if (provenance.startsWith("llm:")) return "llm";
  return "other";
}

/** Where a module's code came from: parts library, scaffold, or an LLM. */
export function ProvenanceChip({ provenance }: { provenance: string }) {
  switch (provenanceKind(provenance)) {
    case "part": {
      const part = provenance.slice("part:".length);
      return (
        <span className="chip chip--accent" title={`Certified parts library: ${part}`}>
          Certified part<span className="sr-only"> ({part})</span>
        </span>
      );
    }
    case "stub":
      return (
        <span className="chip chip--warn" title="Scaffold only: interfaces generated, behaviour left to implement">
          Stub
        </span>
      );
    case "llm": {
      const model = provenance.slice("llm:".length);
      return (
        <span className="chip chip--info" title={`Fabricated by ${model}`}>
          LLM-fabricated<span className="sr-only"> ({model})</span>
        </span>
      );
    }
    default:
      return (
        <span className="chip" title={provenance}>
          {provenance || "Unknown"}
        </span>
      );
  }
}

function ProvenanceSummary({ modules }: { modules: ModuleBuild[] }) {
  const counts = { part: 0, stub: 0, llm: 0, other: 0 };
  for (const module of modules) counts[provenanceKind(module.provenance)] += 1;
  return (
    <div className="summary-chips" aria-label="Module provenance summary">
      <span className="vx-label">{modules.length} modules</span>
      {counts.part > 0 && <span className="chip chip--accent">{counts.part} certified</span>}
      {counts.llm > 0 && <span className="chip chip--info">{counts.llm} LLM-fabricated</span>}
      {counts.stub > 0 && <span className="chip chip--warn">{counts.stub} stub</span>}
      {counts.other > 0 && <span className="chip">{counts.other} other</span>}
    </div>
  );
}

interface Props {
  job: JobRecord;
  onViewCode: (path: string) => void;
}

/** Module build records with provenance and per-module downloads. */
export function ModulesTab({ job, onViewCode }: Props) {
  const paths = useMemo(() => new Set(job.artifacts.map((a) => a.path)), [job.artifacts]);
  const finished = isJobTerminal(job.status);

  if (job.modules.length === 0) {
    return (
      <EmptyState
        text="Awaiting output…"
        hint="Modules are listed here as the Engineers fabricate them."
      />
    );
  }

  return (
    <>
      <ProvenanceSummary modules={job.modules} />
      <div className="table-wrap">
        <table className="table modules-table">
          <caption className="sr-only">Generated modules</caption>
          <thead>
            <tr>
              <th scope="col">Subsystem</th>
              <th scope="col">Module</th>
              <th scope="col">Provenance</th>
              <th scope="col">Responsibility</th>
              <th scope="col">
                <span className="sr-only">Actions</span>
              </th>
            </tr>
          </thead>
          <tbody>
            {job.modules.map((module) => {
              const hasCode = paths.has(module.path);
              return (
                <tr key={module.id}>
                  <td className="mono dim">{module.subsystem}</td>
                  <td>
                    <div className="module-name">{module.name}</div>
                    <div className="module-class">{module.class_name}</div>
                  </td>
                  <td>
                    <ProvenanceChip provenance={module.provenance} />
                  </td>
                  <td>
                    {module.responsibility}
                    {module.notes.length > 0 && (
                      <ul className="module-notes">
                        {module.notes.map((note, index) => (
                          <li key={index}>{note}</li>
                        ))}
                      </ul>
                    )}
                  </td>
                  <td>
                    <div className="module-actions">
                      <button
                        type="button"
                        className="btn btn--sm"
                        disabled={!hasCode}
                        title={hasCode ? module.path : "Code not generated yet"}
                        aria-label={`View code for ${module.name}`}
                        onClick={() => onViewCode(module.path)}
                      >
                        View code
                      </button>
                      {finished && hasCode ? (
                        <a
                          className="btn btn--sm btn--ghost"
                          href={moduleBundleUrl(job.id, module.id)}
                          download={`${module.id}.zip`}
                          aria-label={`Download ${module.name} module (.zip)`}
                        >
                          Download (.zip)
                        </a>
                      ) : (
                        <button
                          type="button"
                          className="btn btn--sm btn--ghost"
                          disabled
                          title="Available when the build has finished"
                        >
                          Download (.zip)
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </>
  );
}
