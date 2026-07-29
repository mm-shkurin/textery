import { describe, expect, it, vi } from 'vitest'
import { screen } from '@testing-library/react'
import * as documentApi from '../../api/documentApi'
import { MAX_AUTOSAVE_ATTEMPTS } from '../../hooks/useDocumentSave'
import {
  defer,
  flushMicrotasks,
  renderCreatedDocument,
  typeAndFireAutosave,
  useAutosaveFailureFakeTimers,
} from './ManualEditor.autosave.testSupport'
import {
  PRODUCTION_SERVER_ERROR,
  SAVED_PLAIN,
  playOutRetrySchedule,
} from './ManualEditor.autosaveFixture'
import {
  DIRTY_BADGE_CLASS,
  RETRYING_BADGE_CLASS,
  SAVE_ERROR_TESTID,
  SAVE_STATUS_BASE_SELECTOR,
  badgeClassName,
} from './ManualEditor.saveStatus.testSupport'

vi.mock('../../api/documentApi')

// The GUARDS around the H9.4 retrying badge, written before the branch existed. The scenario's own
// RED (ManualEditor.autosaveBackoffWindowVisibility) observes exactly ONE instant — inside the
// backoff gap — through `container.querySelector(...)?.className`. Everywhere else the cheapest
// green is free, and each case below closes one of those escapes:
//
//   - the badge must not claim a retry is pending merely because a save is IN FLIGHT (isSaving is
//     set before saveDocument is even called, so deriving the branch from it would ship the badge
//     lying on every ordinary successful save);
//   - the badge must be a SINGLE element, not a retrying span rendered beside the dirty one — the
//     RED's querySelector returns the first match and would pass either way;
//   - it must be an <output>, for the same reason --failed is (it swaps in in place, so assistive
//     tech must hear it) — className alone matches a silent <span>;
//   - and it must not survive the ladder's terminal exit, where the «не сохранено» banner
//     appears and a stuck --retrying would contradict it on screen.

// The guards below are driven through PRODUCTION_SERVER_ERROR (500), NOT the 503 the scenario's own
// fixture uses: the retry-pending signal is validated on the branch production actually takes. See
// the constant's own note in ManualEditor.autosaveFixture.

function badges(container: HTMLElement): NodeListOf<Element> {
  return container.querySelectorAll(SAVE_STATUS_BASE_SELECTOR)
}

// Exactly one save-status element, carrying exactly the one expected modifier. The count is half the
// assertion: without it a green that renders the new branch NEXT to the old one passes on DOM order
// alone, with «Черновик, ещё не сохранён» still on screen beside it.
function expectSoleBadge(container: HTMLElement, modifier: string): Element {
  expect(badges(container)).toHaveLength(1)
  const badge = badges(container)[0]
  expect(badge.className).toBe(badgeClassName(modifier))
  return badge
}

describe('ManualEditor — what the retrying badge must NOT say (H9.4 guards)', () => {
  useAutosaveFailureFakeTimers()

  it('does not claim a retry is pending while the first attempt is still in flight', async () => {
    const { container } = await renderCreatedDocument()
    // Held open deliberately: this is the state `isSaving` describes from the millisecond before
    // saveDocument is called until it settles. Nothing has failed yet, so nothing is being retried.
    const attempt = defer()
    vi.mocked(documentApi.saveDocument).mockReturnValue(attempt.promise)

    await typeAndFireAutosave(SAVED_PLAIN)
    expect(documentApi.saveDocument).toHaveBeenCalledTimes(1)

    // The happy path passes through this exact state on every single save. A badge reading
    // "retrying" here is the scenario's own lie told in the opposite direction.
    expectSoleBadge(container, DIRTY_BADGE_CLASS)

    // And only once the attempt is actually rejected does the branch turn on — which is what makes
    // the assertion above a statement about the SIGNAL, not about the badge never rendering.
    attempt.reject(PRODUCTION_SERVER_ERROR)
    await flushMicrotasks()
    expectSoleBadge(container, RETRYING_BADGE_CLASS)
  })

  it('announces the retrying badge to assistive tech, as the failed badge already is', async () => {
    const { container } = await renderCreatedDocument()
    vi.mocked(documentApi.saveDocument).mockRejectedValue(PRODUCTION_SERVER_ERROR)

    await typeAndFireAutosave(SAVED_PLAIN)

    // <output> has role=status implicitly. This badge replaces «Черновик…» in place with no
    // focus change and no other on-screen movement, so a screen-reader user is told a save failed
    // only if the element announces itself — a <span> with the right class says nothing at all.
    const badge = expectSoleBadge(container, RETRYING_BADGE_CLASS)
    expect(badge.tagName).toBe('OUTPUT')
    expect(screen.getByRole('status')).toBe(badge)
  })

  it('drops the retrying badge when the ladder gives up, leaving one dirty badge', async () => {
    const { container } = await renderCreatedDocument()
    vi.mocked(documentApi.saveDocument).mockRejectedValue(PRODUCTION_SERVER_ERROR)

    await typeAndFireAutosave(SAVED_PLAIN)
    expectSoleBadge(container, RETRYING_BADGE_CLASS)

    await playOutRetrySchedule()

    // Terminal exit: the budget is spent and the banner is up. A retry-pending flag cleared only in
    // the retry callback or on a clean settle sticks here forever — «повторяем…» co-rendered
    // with «не сохранено», the user waiting on a ladder that burned out seconds ago.
    expect(documentApi.saveDocument).toHaveBeenCalledTimes(MAX_AUTOSAVE_ATTEMPTS)
    expect(screen.getByTestId(SAVE_ERROR_TESTID)).toBeInTheDocument()
    expectSoleBadge(container, DIRTY_BADGE_CLASS)
  })
})
