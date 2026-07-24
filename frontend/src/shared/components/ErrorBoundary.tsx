import { Component, type ErrorInfo, type ReactNode } from 'react'

interface ErrorBoundaryProps {
  children: ReactNode
  // What to say when the subtree dies. Named per boundary, because "editor" and "page" are not
  // the same news to the person reading it.
  title: string
  // Offered only when the caller has somewhere safe to send them; a button that reloads into the
  // same crash is worse than no button.
  onRecover?: () => void
  recoverLabel?: string
}

interface ErrorBoundaryState {
  hasError: boolean
}

// The app's only class component, and it has to be one: `componentDidCatch` has no hook
// equivalent — React exposes render-phase error recovery through this lifecycle alone.
//
// Without a boundary anywhere, ANY throw below the root unmounts the entire tree and leaves a
// blank white page. That is the realistic failure for ManualEditor in particular: Tiptap and
// ProseMirror are the largest and least-controlled dependency here, they run on live DOM
// selection state, and a throw inside a transaction takes the app with it. The user then loses
// unsaved text with nothing on screen to explain why — the one outcome the save flow exists to
// prevent.
export class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  state: ErrorBoundaryState = { hasError: false }

  static getDerivedStateFromError(): ErrorBoundaryState {
    return { hasError: true }
  }

  // There is no reporting sink in this app, so `console.error` is not laziness — it is the only
  // trace a crash leaves, and it is why `.oxlintrc.json` allows `console.error` while banning
  // `console.log`. Route this to a real sink when one exists; do not delete it before then.
  componentDidCatch(error: Error, info: ErrorInfo): void {
    console.error('Unhandled error in React subtree', error, info.componentStack)
  }

  private handleRecover = (): void => {
    // Clear the flag as part of recovering, or the boundary keeps rendering the failure state
    // over a subtree the caller has already navigated away from.
    this.setState({ hasError: false })
    this.props.onRecover?.()
  }

  render(): ReactNode {
    if (!this.state.hasError) {
      return this.props.children
    }

    return (
      <div className="error-boundary" role="alert" data-testid="error-boundary">
        <p className="error-boundary-title">{this.props.title}</p>
        {this.props.onRecover && (
          <button type="button" onClick={this.handleRecover}>
            {this.props.recoverLabel ?? 'Вернуться'}
          </button>
        )}
      </div>
    )
  }
}
