import { Fragment } from "react";

import { CHAIN_OF_COMMAND } from "../../lib/status";

/** "COMMANDER ▸ ARCHITECT ▸ DRAFTSMAN / INTEGRATOR / ENGINEERS ▸ INSPECTOR ▸ QUARTERMASTER" */
export function ChainOfCommand() {
  return (
    <ol className="chain" aria-label="Agent chain of command">
      {CHAIN_OF_COMMAND.map((stage, index) => (
        <li key={stage.map((agent) => agent.role).join("-")} className="chain__stage">
          {index > 0 && (
            <span className="chain__sep" aria-hidden="true">
              ▸
            </span>
          )}
          {stage.map((agent, position) => (
            <Fragment key={agent.role}>
              {position > 0 && (
                <span className="chain__sep" aria-hidden="true">
                  /
                </span>
              )}
              <span data-role={agent.role}>{agent.name}</span>
            </Fragment>
          ))}
        </li>
      ))}
    </ol>
  );
}
