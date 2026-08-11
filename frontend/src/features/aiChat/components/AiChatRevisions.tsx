import { useState } from 'react'

export const REVISIONS_TOGGLE_LABEL = 'История правок'
// What the panel says while it has nothing to list. The revision ROWS are read by
// `GET /revisions`, which scenario 1.3 owns and this unit must not pull forward — but an empty
// container that says nothing would read as a broken panel rather than an unfinished one.
export const REVISIONS_EMPTY_NOTICE = 'История правок появится здесь.'

// The revisions control and its panel, deliberately OUTSIDE the quota branch: a spent daily
// quota stops new instructions, it does not take away the history of the ones already applied.
// An over-quota page that greyed the whole panel out is exactly the regression scenario 0.2
// forbids, so the toggle's enabled state is never conditioned on quota at all.
export function AiChatRevisions() {
  const [isOpen, setIsOpen] = useState(false)

  return (
    <div className="ac-chat-revisions">
      <button
        type="button"
        className="ac-chat-revisions-toggle"
        data-testid="ai-chat-revisions-toggle"
        aria-expanded={isOpen}
        onClick={() => setIsOpen((open) => !open)}
      >
        {REVISIONS_TOGGLE_LABEL}
      </button>
      {isOpen ? (
        <div className="ac-chat-revisions-panel" data-testid="ai-chat-revisions-panel">
          <p className="ac-chat-revisions-empty">{REVISIONS_EMPTY_NOTICE}</p>
        </div>
      ) : null}
    </div>
  )
}
