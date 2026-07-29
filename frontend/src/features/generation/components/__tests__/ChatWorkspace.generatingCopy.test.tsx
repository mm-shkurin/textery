import { describe, expect, it, vi } from 'vitest'
import { render, screen, within } from '@testing-library/react'
import { ChatWorkspace } from '../ChatWorkspace'

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
    render(
      <ChatWorkspace
        documentType="referat"
        documentTypeLabel="Реферат"
        state="pending"
        content={null}
        volumePages={null}
        error={null}
        onSubmit={vi.fn()}
        onReset={vi.fn()}
      />,
    )

    const generating = screen.getByTestId('generation-generating')
    expect(within(generating).getByRole('heading')).toHaveTextContent(/^Готовим ваш реферат$/)
    expect(
      within(screen.getByTestId('chat-panel')).getByText('ИИ пишет реферат'),
    ).toBeInTheDocument()
  })

  // The possessive declines with gender, so composing 'ваш' as a constant is grammatical for
  // доклад/реферат and wrong for эссе/сочинение — the failure a Record-per-form table prevents and
  // a single template string would not.
  it('agrees the possessive with a neuter document type', () => {
    render(
      <ChatWorkspace
        documentType="sochinenie"
        documentTypeLabel="Сочинение"
        state="pending"
        content={null}
        volumePages={null}
        error={null}
        onSubmit={vi.fn()}
        onReset={vi.fn()}
      />,
    )

    expect(
      within(screen.getByTestId('generation-generating')).getByRole('heading'),
    ).toHaveTextContent(/^Готовим ваше сочинение$/)
  })
})
