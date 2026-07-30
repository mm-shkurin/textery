import { describe, expect, it, vi } from 'vitest'
import { render, screen, within } from '@testing-library/react'
import { ChatWorkspace } from '../ChatWorkspace'
import type { ComponentProps } from 'react'
import { DOCUMENT_TYPE_LABELS } from '../../../../shared/documentTypes'

type WorkspaceProps = ComponentProps<typeof ChatWorkspace>

// One run, one workspace, several states — the component is not remounted across a generation, so
// the chat panel keeps every step on screen and the doc area swaps in place. Rerendering is
// therefore the honest way to observe what the user actually reads over a session; rendering each
// state afresh would hide exactly the inconsistency this file exists to catch.
function renderRun() {
  const props = (state: WorkspaceProps['state'], extra: Partial<WorkspaceProps> = {}) => ({
    documentType: 'referat' as const,
    documentTypeLabel: DOCUMENT_TYPE_LABELS.referat,
    state,
    content: null,
    volumePages: null,
    error: null,
    onSubmit: vi.fn(),
    onReset: vi.fn(),
    ...extra,
  })
  const { rerender } = render(<ChatWorkspace {...props('pending')} />)
  return (state: WorkspaceProps['state'], extra: Partial<WorkspaceProps> = {}) =>
    rerender(<ChatWorkspace {...props(state, extra)} />)
}

describe('ChatWorkspace transcript copy', () => {
  // Scenario 1.2 made the pending line decline. Leaving the later steps hardcoded would have had
  // one panel say 'ИИ пишет реферат' and, one state later, 'Пишу доклад' — two document types
  // named to the same user about the same run. The generating-copy suite cannot see this: it never
  // leaves `pending`.
  it('names one document type across a whole run, not one per state', () => {
    const setState = renderRun()

    const panel = () => within(screen.getByTestId('chat-panel'))
    expect(panel().getByText('ИИ пишет реферат')).toBeInTheDocument()

    setState('completed', { content: '# Готово', volumePages: 3 })
    expect(panel().getByText('Пишу реферат')).toBeInTheDocument()
    expect(panel().queryByText(/доклад/)).not.toBeInTheDocument()

    setState('failed', { error: 'Провайдер недоступен' })
    expect(within(screen.getByTestId('doc-error')).getByRole('heading')).toHaveTextContent(
      /^Не удалось сгенерировать реферат$/,
    )
  })

  it('prompts for a topic in the picked type when the run is reset', () => {
    const setState = renderRun()

    setState('idle')

    expect(screen.getByRole('heading', { name: 'Опишите тему реферата' })).toBeInTheDocument()
  })

  // The failed panel's 24px gap above its button comes from `.doc-placeholder p + .cw-btn`, added
  // when the paragraph's unconditional bottom margin was removed for the generating screen. jsdom
  // applies no CSS, so nothing observes that gap; what a test CAN pin is the selector's premise —
  // that this button carries `cw-btn`. Renaming the class or wrapping the button in an extracted
  // component silently drops the gap with the whole suite green.
  it('keeps the failed panel button on the class its spacing rule selects', () => {
    const setState = renderRun()

    setState('failed', { error: 'Провайдер недоступен' })

    expect(screen.getByTestId('error-reset')).toHaveClass('cw-btn')
  })
})
