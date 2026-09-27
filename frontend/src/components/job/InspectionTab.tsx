import type { CheckStatus, InspectionReport } from "../../api/types";
import { cx } from "../../lib/cx";
import { EmptyState } from "../States";
import { CheckStatusIcon, Glyph } from "../Status";

const ORDER: Record<CheckStatus, number> = { fail: 0, warn: 1, pass: 2 };
const LABEL: Record<CheckStatus, string> = { pass: "Pass", warn: "Warn", fail: "Fail" };
const CHIP: Record<CheckStatus, string> = { pass: "chip--accent", warn: "chip--warn", fail: "chip--danger" };

/** Count per status, trusting the server's counts and falling back to the checks. */
export function checkCounts(report: InspectionReport): Record<CheckStatus, number> {
  const count = (status: CheckStatus) =>
    report.counts?.[status] ?? report.checks.filter((check) => check.status === status).length;
  return { pass: count("pass"), warn: count("warn"), fail: count("fail") };
}

/** The Inspector's report: verdict, counts, then checks (failures first). */
export function InspectionTab({ inspection }: { inspection: InspectionReport | null }) {
  if (!inspection) {
    return <EmptyState text="Pending — the Inspector has not reported yet." />;
  }

  const counts = checkCounts(inspection);
  const checks = inspection.checks
    .map((check, index) => ({ check, index }))
    .sort((a, b) => (ORDER[a.check.status] ?? 3) - (ORDER[b.check.status] ?? 3) || a.index - b.index)
    .map(({ check }) => check);

  return (
    <>
      <div className="summary-chips">
        <span className={cx("chip", "verdict", inspection.passed ? "chip--accent" : "chip--danger")}>
          <Glyph kind={inspection.passed ? "check" : "cross"} size={12} />
          {inspection.passed ? "Inspection passed" : "Inspection failed"}
        </span>
        {(["pass", "warn", "fail"] as const).map((status) => (
          <span key={status} className={cx("chip", CHIP[status])}>
            {LABEL[status]} {counts[status]}
          </span>
        ))}
      </div>
      {checks.length === 0 ? (
        <EmptyState compact text="No checks reported" />
      ) : (
        <ul className="check-list" aria-label="Inspection checks">
          {checks.map((check, index) => (
            <li key={`${check.id}-${index}`} className="check">
              <span className="check__icon">
                <CheckStatusIcon status={check.status} />
              </span>
              <div>
                <div className="check__head">
                  <span className={cx("check__status", `tone-${check.status}`)}>
                    {LABEL[check.status] ?? check.status}
                  </span>
                  <span className="check__title">{check.title}</span>
                  {check.target && <code className="check__target">{check.target}</code>}
                </div>
                {check.detail && <p className="check__detail">{check.detail}</p>}
              </div>
            </li>
          ))}
        </ul>
      )}
    </>
  );
}
