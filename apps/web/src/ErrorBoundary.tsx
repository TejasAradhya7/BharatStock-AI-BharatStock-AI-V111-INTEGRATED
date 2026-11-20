import React from 'react';

type Props = { children: React.ReactNode };
type State = { failed: boolean; message: string };

/** Prevent an unexpected React render error from leaving the dashboard as a blank page. */
export default class ErrorBoundary extends React.Component<Props, State> {
  state: State = { failed: false, message: '' };

  static getDerivedStateFromError(error: unknown): State {
    return {
      failed: true,
      message: error instanceof Error ? error.message : 'An unexpected interface error occurred.',
    };
  }

  componentDidCatch(error: Error, info: React.ErrorInfo) {
    // Log locally for browser debugging; do not send market data or credentials to a third party.
    console.error('BharatStock dashboard render failure:', error, info.componentStack);
  }

  private recover = () => {
    this.setState({ failed: false, message: '' });
  };

  render() {
    if (!this.state.failed) return this.props.children;
    return (
      <main className="appError" role="alert" aria-live="assertive">
        <div className="appErrorCard">
          <div className="appErrorIcon" aria-hidden="true">!</div>
          <p className="appErrorEyebrow">BHARATSTOCK AI</p>
          <h1>The dashboard hit an unexpected error</h1>
          <p className="appErrorText">Your page could not finish rendering. Try recovering the dashboard. If the issue continues, reload the page and check the browser console.</p>
          {import.meta.env.DEV && this.state.message && <pre className="appErrorDetails">{this.state.message}</pre>}
          <div className="appErrorActions">
            <button className="primary" onClick={this.recover}>Try again</button>
            <button className="appErrorSecondary" onClick={() => window.location.reload()}>Reload page</button>
          </div>
        </div>
      </main>
    );
  }
}
