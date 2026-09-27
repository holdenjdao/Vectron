import { Component, type ErrorInfo, type ReactNode } from "react";

import { Callout } from "./Callout";

interface Props {
  children: ReactNode;
}

interface State {
  error: Error | null;
}

/** Last line of defence: a rendering bug in one view shows a message instead of a blank page. */
export class ErrorBoundary extends Component<Props, State> {
  state: State = { error: null };

  static getDerivedStateFromError(error: Error): State {
    return { error };
  }

  componentDidCatch(error: Error, info: ErrorInfo): void {
    console.error("Vectron view crashed:", error, info.componentStack);
  }

  render(): ReactNode {
    const { error } = this.state;
    if (!error) return this.props.children;
    return (
      <Callout
        tone="danger"
        title="This view failed to render"
        actions={
          <button type="button" className="btn btn--sm" onClick={() => this.setState({ error: null })}>
            Try again
          </button>
        }
      >
        {error.message || String(error)}
      </Callout>
    );
  }
}
