import { describe, expect, it, vi } from 'vitest'
import { render, screen, within } from '@testing-library/react'
import { ChatWorkspace } from '../ChatWorkspace'
import type { DocumentType } from '../../../../shared/documentTypes'
import { DOCUMENT_TYPE_LABELS } from '../../../../shared/documentTypes'

// The generating screen is the whole subject here, so every case renders the same workspace in
// `pending` and varies only the picked type. The label is looked up rather than passed in: a case
// that named a type and then mislabelled it would be testing a caller mistake, not this copy.
function renderGenerating(documentType: DocumentType) {
  render(
    <ChatWorkspace
      documentType={documentType}
      documentTypeLabel={DOCUMENT_TYPE_LABELS[documentType]}
      state="pending"
      content={null}
      volumePages={null}
      error={null}
      onSubmit={vi.fn()}
      onReset={vi.fn()}
    />,
  )
}

// Mockup 05 (chat-pending) names the document type twice on the generating screen: the doc area's
// title ('Готовим ваш доклад') and the chat panel's progress line ('ИИ пишет доклад'). Both were
// hardcoded to 'доклад' while the same screen's status badge and the run itself carry the type the
// user actually picked — the defect /design-review already failed Composer.tsx for one scenario
// earlier, in the two places scenario 1.2 is about.
//
// 'referat' rather than 'doklad' deliberately: against the hardcoded literals a doklad render
// passes, so it would assert nothing. Renders through ChatWorkspace rather than DocArea/Progress
// directly, because the prop join is what a caller can get wrong.
describe('ChatWorkspace generating copy', () => {
  it('names the picked document type in both halves of the generating screen', () => {
    renderGenerating('referat')

    const generating = screen.getByTestId('generation-generating')
    expect(within(generating).getByRole('heading')).toHaveTextContent(/^Готовим ваш реферат$/)
    expect(
      within(screen.getByTestId('chat-panel')).getByText('ИИ пишет реферат'),
    ).toBeInTheDocument()
  })

  // The doklad rendering is pinned here because two Python constants transcribe it by EQUALITY —
  // `generating_state_locators.py` EXPECTED_GENERATING_DOC_TEXT / EXPECTED_GENERATING_PANEL_TEXT,
  // scenario 1.2's Selenium witness that the generating state is up. They were literals read off
  // the components; since this unit they are the output of generatingTitle('doklad') and
  // writingProgressMessage('doklad'), and no other executing test renders doklad's generating copy.
  // Without this case, editing DOCUMENT_TYPE_ACCUSATIVE.doklad or either template keeps the whole
  // vitest suite green while invalidating both pins — and the failure would surface only at
  // green-selenium, as a text mismatch on the assertion that means "generating state not shown",
  // pointing at polling rather than at a copy string.
  it('renders the exact doklad copy the Selenium locators transcribe', () => {
    renderGenerating('doklad')

    expect(
      within(screen.getByTestId('generation-generating')).getByRole('heading'),
    ).toHaveTextContent(/^Готовим ваш доклад$/)
    expect(
      within(screen.getByTestId('chat-panel')).getByText('ИИ пишет доклад'),
    ).toBeInTheDocument()
  })

  // The possessive declines with gender, so composing 'ваш' as a constant is grammatical for
  // доклад/реферат and wrong for эссе/сочинение — the failure a Record-per-form table prevents and
  // a single template string would not.
  it('agrees the possessive with a neuter document type', () => {
    renderGenerating('sochinenie')

    expect(
      within(screen.getByTestId('generation-generating')).getByRole('heading'),
    ).toHaveTextContent(/^Готовим ваше сочинение$/)
  })
})
