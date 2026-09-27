import { useId, useMemo, useState, type FormEvent } from "react";

import { createJob, errorMessage } from "../../api/client";
import type { BlueprintOption, BlueprintSummary, BuildRequest } from "../../api/types";
import { navigate, routes } from "../../hooks/useHashRoute";
import { CATEGORY_LABEL } from "../../lib/status";
import { Callout } from "../Callout";
import { OptionField, type DraftValue } from "./OptionField";

type Draft = Record<string, DraftValue>;
type OptionValues = NonNullable<BuildRequest["options"]>;

function toDraft(option: BlueprintOption): DraftValue {
  if (option.type === "boolean") return option.default === true || option.default === "true";
  return option.default == null ? "" : String(option.default);
}

function defaultDraft(options: BlueprintOption[]): Draft {
  return Object.fromEntries(options.map((option) => [option.key, toDraft(option)]));
}

/** Converts edited values into the request payload, collecting per-option errors. */
function resolveDraft(options: BlueprintOption[], draft: Draft) {
  const values: OptionValues = {};
  const errors: Record<string, string> = {};
  for (const option of options) {
    const raw = draft[option.key];
    if (option.type === "boolean") {
      values[option.key] = raw === true;
      continue;
    }
    if (option.type === "choice") {
      values[option.key] = String(raw ?? option.default);
      continue;
    }
    const text = String(raw ?? "").trim();
    const number = Number(text);
    const unit = option.unit ? ` ${option.unit}` : "";
    if (text === "" || !Number.isFinite(number)) errors[option.key] = "Enter a number.";
    else if (option.min != null && number < option.min)
      errors[option.key] = `Must be at least ${option.min}${unit}.`;
    else if (option.max != null && number > option.max)
      errors[option.key] = `Must be at most ${option.max}${unit}.`;
    else values[option.key] = number;
  }
  return { values, errors };
}

interface Props {
  blueprint: BlueprintSummary;
  /** Mission brief from the catalog; attached to the build when non-empty. */
  brief: string;
}

export function BlueprintCard({ blueprint, brief }: Props) {
  const idBase = useId();
  const defaults = useMemo(() => defaultDraft(blueprint.options), [blueprint.options]);
  const [draft, setDraft] = useState<Draft>(defaults);
  const [configOpen, setConfigOpen] = useState(false);
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const trimmedBrief = brief.trim();
  const modified = blueprint.options.filter((o) => draft[o.key] !== defaults[o.key]).length;
  const optionCount = blueprint.options.length;

  const update = (key: string, value: DraftValue) => {
    setDraft((prev) => ({ ...prev, [key]: value }));
    setFieldErrors((prev) => {
      if (!(key in prev)) return prev;
      const next = { ...prev };
      delete next[key];
      return next;
    });
  };

  const resetDefaults = () => {
    setDraft(defaults);
    setFieldErrors({});
  };

  const build = async (event: FormEvent) => {
    event.preventDefault();
    if (submitting) return;
    const { values, errors } = resolveDraft(blueprint.options, draft);
    setFieldErrors(errors);
    if (Object.keys(errors).length > 0) {
      setConfigOpen(true);
      setError("Fix the highlighted options before building.");
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      const request: BuildRequest = { blueprint_id: blueprint.id, options: values };
      if (trimmedBrief) request.brief = trimmedBrief;
      const job = await createJob(request);
      navigate(routes.job(job.id));
    } catch (err) {
      setError(errorMessage(err));
      setSubmitting(false);
    }
  };

  const nameId = `${idBase}-name`;
  const configId = `${idBase}-config`;

  return (
    <article className="bp-card" aria-labelledby={nameId}>
      <div className="bp-card__top">
        <span className="bp-card__designation">{blueprint.designation}</span>
        <span className="chip chip--sm">{CATEGORY_LABEL[blueprint.category] ?? blueprint.category}</span>
      </div>
      <h3 className="bp-card__name" id={nameId}>
        {blueprint.name}
      </h3>
      <p className="bp-card__summary">{blueprint.summary}</p>
      <p className="bp-card__stats">
        <strong>{blueprint.stats.subsystems}</strong> subsystems ·{" "}
        <strong>{blueprint.stats.modules}</strong> modules
      </p>

      <form className="bp-card__form" onSubmit={build} noValidate>
        {optionCount > 0 && (
          <div className="bp-config">
            <button
              type="button"
              className="bp-config__toggle"
              aria-expanded={configOpen}
              aria-controls={configId}
              onClick={() => setConfigOpen((open) => !open)}
            >
              <span className="bp-config__chevron" aria-hidden="true">
                ▸
              </span>
              Configure · {optionCount} {optionCount === 1 ? "option" : "options"}
              {modified > 0 && <span className="bp-config__modified">{modified} modified</span>}
            </button>
            <div id={configId} className="bp-config__fields" hidden={!configOpen}>
              {blueprint.options.map((option) => (
                <OptionField
                  key={option.key}
                  idBase={idBase}
                  option={option}
                  value={draft[option.key]}
                  error={fieldErrors[option.key]}
                  onChange={(value) => update(option.key, value)}
                />
              ))}
              {modified > 0 && (
                <button type="button" className="link-button bp-config__reset" onClick={resetDefaults}>
                  Reset to defaults
                </button>
              )}
            </div>
          </div>
        )}

        <div className="bp-card__footer">
          {trimmedBrief && (
            <p className="bp-card__attach">
              <span aria-hidden="true">+</span> Mission brief attached
            </p>
          )}
          {error && <Callout tone="danger">{error}</Callout>}
          <button
            type="submit"
            className="btn btn--primary btn--block"
            disabled={submitting}
            aria-label={`Build ${blueprint.name}`}
          >
            {submitting ? "Launching…" : "Build"} <span aria-hidden="true">▸</span>
          </button>
        </div>
      </form>
    </article>
  );
}
