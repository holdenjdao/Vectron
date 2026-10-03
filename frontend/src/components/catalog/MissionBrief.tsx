import { useState, type FormEvent, type KeyboardEvent } from "react";

import { createJob, errorMessage } from "../../api/client";
import { navigate, routes } from "../../hooks/useHashRoute";
import { Callout } from "../Callout";
import { Panel } from "../Panel";

/** Backend limit (BuildRequest.brief max_length). */
export const BRIEF_MAX_LENGTH = 4000;

interface Props {
  brief: string;
  onBriefChange: (brief: string) => void;
}

/** Free-text mission brief: builds on its own, and rides along with blueprint builds. */
export function MissionBrief({ brief, onBriefChange }: Props) {
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const trimmed = brief.trim();

  const submit = async (event?: FormEvent) => {
    event?.preventDefault();
    if (!trimmed || submitting) return;
    setSubmitting(true);
    setError(null);
    try {
      const job = await createJob({ brief: trimmed });
      navigate(routes.job(job.id));
    } catch (err) {
      setError(errorMessage(err));
      setSubmitting(false);
    }
  };

  const onKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === "Enter" && (event.ctrlKey || event.metaKey)) {
      event.preventDefault();
      void submit();
    }
  };

  return (
    <Panel
      title="Mission brief"
      meta={
        <span className="num">
          {brief.length} / {BRIEF_MAX_LENGTH}
        </span>
      }
    >
      <form className="brief__form" onSubmit={submit}>
        <div>
          <label className="sr-only" htmlFor="mission-brief">
            Mission brief
          </label>
          <textarea
            id="mission-brief"
            className="textarea"
            rows={3}
            maxLength={BRIEF_MAX_LENGTH}
            value={brief}
            onChange={(event) => onBriefChange(event.target.value)}
            onKeyDown={onKeyDown}
            placeholder="Optional — e.g. 'Small drone for night-time perimeter surveillance of a forward operating base'"
            aria-describedby="mission-brief-note"
          />
          <span className="brief__hint" aria-hidden="true">
            <span className="kbd">Ctrl</span> + <span className="kbd">Enter</span> to build from the brief
          </span>
        </div>
        <div className="brief__side">
          <p className="brief__note" id="mission-brief-note">
            The brief is also attached to any blueprint build below.
          </p>
          <button type="submit" className="btn btn--primary" disabled={!trimmed || submitting}>
            {submitting ? "Launching…" : "Build from brief"}
          </button>
        </div>
        {error && (
          <Callout tone="danger" className="brief__error">
            {error}
          </Callout>
        )}
      </form>
    </Panel>
  );
}
