import type { BlueprintOption } from "../../api/types";

/** Form value while editing: numbers stay strings until submit so partial input is allowed. */
export type DraftValue = string | boolean;

interface Props {
  idBase: string;
  option: BlueprintOption;
  value: DraftValue | undefined;
  error?: string;
  onChange: (value: DraftValue) => void;
}

function rangeText(option: BlueprintOption): string | null {
  const unit = option.unit ? ` ${option.unit}` : "";
  if (option.min != null && option.max != null) return `Range ${option.min}–${option.max}${unit}`;
  if (option.min != null) return `Minimum ${option.min}${unit}`;
  if (option.max != null) return `Maximum ${option.max}${unit}`;
  return null;
}

/** One blueprint build option: choice → select, number → input + unit, boolean → checkbox. */
export function OptionField({ idBase, option, value, error, onChange }: Props) {
  const id = `${idBase}-opt-${option.key}`;
  const range = option.type === "number" ? rangeText(option) : null;
  const help = [option.help, range].filter(Boolean).join(" · ");
  const helpId = help ? `${id}-help` : undefined;
  const errorId = error ? `${id}-error` : undefined;
  const describedBy = [helpId, errorId].filter(Boolean).join(" ") || undefined;

  const notes = (
    <>
      {help && (
        <p className="field__help" id={helpId}>
          {help}
        </p>
      )}
      {error && (
        <p className="field__error" id={errorId}>
          {error}
        </p>
      )}
    </>
  );

  if (option.type === "boolean") {
    return (
      <div className="field field--check">
        <input
          id={id}
          type="checkbox"
          className="checkbox"
          checked={value === true}
          onChange={(event) => onChange(event.target.checked)}
          aria-describedby={describedBy}
        />
        <label className="field__label" htmlFor={id}>
          {option.label}
        </label>
        {notes}
      </div>
    );
  }

  if (option.type === "choice") {
    return (
      <div className="field">
        <label className="field__label" htmlFor={id}>
          {option.label}
        </label>
        <select
          id={id}
          className="select"
          value={String(value ?? "")}
          onChange={(event) => onChange(event.target.value)}
          aria-describedby={describedBy}
        >
          {option.choices.map((choice) => (
            <option key={choice.value} value={choice.value}>
              {choice.label}
            </option>
          ))}
        </select>
        {notes}
      </div>
    );
  }

  return (
    <div className="field">
      <label className="field__label" htmlFor={id}>
        {option.label}
        {option.unit && <span className="sr-only"> ({option.unit})</span>}
      </label>
      <div className="input-unit">
        <input
          id={id}
          type="number"
          inputMode="decimal"
          className="input mono"
          value={String(value ?? "")}
          min={option.min ?? undefined}
          max={option.max ?? undefined}
          step={option.step ?? "any"}
          onChange={(event) => onChange(event.target.value)}
          aria-invalid={error ? true : undefined}
          aria-describedby={describedBy}
        />
        {option.unit && (
          <span className="input-unit__unit" aria-hidden="true">
            {option.unit}
          </span>
        )}
      </div>
      {notes}
    </div>
  );
}
