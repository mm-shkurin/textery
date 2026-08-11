import type { EditQuotaState } from '../api/editQuotaApi'

export const COMPOSER_PLACEHOLDER = 'Напишите, что нужно изменить'
export const SEND_LABEL = 'Отправить'
// The invariant half of the sentence `mockups/desktop/06-over-quota.html` renders. Its tail is a
// wall-clock countdown ("через 6 ч 12 мин") that no literal can pin, which is why the lead has an
// element of its own instead of the whole hint being matched by prefix.
export const QUOTA_RESET_HINT_LEAD = 'Дневной лимит правок исчерпан'

interface AiChatComposerProps {
  quota: EditQuotaState
}

// The instruction composer. Rendered only once the quota is KNOWN (see AiChatPanel): a composer
// that appears live and goes dead a tick later invites the user to start typing an instruction
// that was never going to be accepted.
//
// Both controls carry the same `disabled` flag. A dead input beside a live send control still
// submits — whatever the composer already held, or an empty instruction — so disabling only the
// input would leave "cannot type an instruction" satisfied on screen and not in fact.
export function AiChatComposer({ quota }: AiChatComposerProps) {
  // One name for the render-level fact the four uses below all restate: the composer is dead.
  // Read once so the box, the input and the send can never disagree about which state they are in.
  const disabled = quota.exhausted
  return (
    <div className="ac-chat-composer">
      {disabled ? <QuotaResetHint resetsAt={quota.resetsAt} /> : null}
      {/* The mockup's `.composer .box`: input and send share ONE bordered field rather than
          sitting as siblings, and the box is what carries the disabled treatment — a field that
          stays live-looking around a greyed control reads as "the send broke", not as "you cannot
          type here". */}
      <div className={`ac-chat-box${disabled ? ' ac-chat-box--disabled' : ''}`}>
        <textarea
          className="ac-chat-input"
          data-testid="ai-chat-message-input"
          placeholder={COMPOSER_PLACEHOLDER}
          aria-label={COMPOSER_PLACEHOLDER}
          rows={3}
          disabled={disabled}
        />
        <div className="ac-chat-box-row">
          <button
            type="button"
            className="ac-chat-send"
            data-testid="ai-chat-send-button"
            disabled={disabled}
          >
            {SEND_LABEL}
          </button>
        </div>
      </div>
    </div>
  )
}

// `data-resets-at` carries the API's own string, byte for byte — no `new Date(...)` on the path,
// which would rewrite `2026-08-11T00:00:00+03:00` to `...Z` and break the byte-equality the
// Selenium layer asserts across two serializations.
function QuotaResetHint({ resetsAt }: { resetsAt: string }) {
  return (
    <p
      className="ac-chat-quota-hint"
      data-testid="ai-chat-quota-reset-hint"
      data-resets-at={resetsAt}
    >
      <span data-testid="ai-chat-quota-reset-hint-lead">{QUOTA_RESET_HINT_LEAD}</span>
    </p>
  )
}
