import { describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen, within } from '@testing-library/react'
import { ChatWorkspace } from '../ChatWorkspace'
import type { ComponentProps } from 'react'
import { EMPTY_PARAMETERS } from '../../utils/generationParameters'

type WorkspaceProps = ComponentProps<typeof ChatWorkspace>

function renderWorkspace(overrides: Partial<WorkspaceProps> = {}) {
  const onSubmit = vi.fn()
  const onReset = vi.fn()
  const props = (extra: Partial<WorkspaceProps> = {}) => ({
    documentType: 'doklad' as const,
    documentTypeLabel: 'Доклад',
    state: 'idle' as const,
    content: null,
    volumePages: null,
    error: null,
    onSubmit,
    onReset,
    ...overrides,
    ...extra,
  })
  const { rerender } = render(<ChatWorkspace {...props()} />)
  // The workspace is never unmounted across a generation — only its inner branches swap — so
  // tests that follow the topic across a state change must rerender rather than render afresh,
  // or they lose the very component state they are asserting about.
  const setState = (extra: Partial<WorkspaceProps>) => rerender(<ChatWorkspace {...props(extra)} />)
  return { onSubmit, onReset, setState }
}

function typeTopic(value: string) {
  fireEvent.change(screen.getByTestId('topic-input'), { target: { value } })
}

describe('ChatWorkspace', () => {
  // Экран перерисован по фрейму «Создание "Тип документа"»: вместо бейджа состояния —
  // три шага, вместо хлебных крошек — заголовок с типом и сводка справа. Оба состояния
  // проверяются, потому что удаление любой из веток раньше оставляло сюиту зелёной.
  it('называет тип документа в заголовке и держит форму на первом шаге', () => {
    renderWorkspace()

    expect(screen.getByRole('heading', { name: 'Создание «Доклад»' })).toBeInTheDocument()
    expect(screen.getByTestId('generation-summary-type')).toHaveTextContent(/^Доклад$/)
    const steps = within(screen.getByTestId('generation-steps')).getAllByRole('listitem')
    expect(steps[0]).toHaveAttribute('aria-current', 'step')
  })

  it('переводит шаг на генерацию и убирает форму, пока идёт прогон', () => {
    renderWorkspace({ state: 'pending' })

    const steps = within(screen.getByTestId('generation-steps')).getAllByRole('listitem')
    expect(steps[1]).toHaveAttribute('aria-current', 'step')
    expect(screen.queryByTestId('topic-input')).not.toBeInTheDocument()
    expect(screen.queryByTestId('generation-summary-type')).not.toBeInTheDocument()
  })

  // documentType and documentTypeLabel arrive as independent props, so a caller can pair a
  // 'referat' id with a 'Доклад' label and put two different type names on one screen — the
  // breadcrumb renders the label, the composer heading renders topicFieldLabel(documentType).
  // DocumentGenerationFlow derives them consistently today; this pins the contract at the
  // component boundary so a future caller cannot silently re-open the bug.
  it('names one and the same document type in the summary and the topic field', () => {
    renderWorkspace({ documentType: 'referat', documentTypeLabel: 'Реферат' })

    expect(screen.getByTestId('generation-summary-type')).toHaveTextContent(/^Реферат$/)
    expect(screen.getByRole('textbox', { name: 'Тема реферата' })).toBeInTheDocument()
  })

  it('disables send button until topic is non-empty', () => {
    renderWorkspace()

    const send = screen.getByTestId('topic-send')
    expect(send).toBeDisabled()

    typeTopic('Тема доклада')
    expect(send).toBeEnabled()
  })

  it('calls onSubmit with trimmed topic', () => {
    const { onSubmit } = renderWorkspace()

    typeTopic('  Тема  ')
    fireEvent.click(screen.getByTestId('topic-send'))

    expect(onSubmit).toHaveBeenCalledTimes(1)
    expect(onSubmit).toHaveBeenCalledWith('Тема', EMPTY_PARAMETERS)
  })

  // The send button is disabled while the topic is blank, but Composer's textarea fires onSend on
  // Ctrl/Cmd+Enter with no disabled guard — so a whitespace-only topic reaches send() and the
  // `if (trimmed)` there is the only thing stopping an empty-topic POST (backend 422). That false
  // branch was the file's single uncovered branch: deleting the `if` left the whole suite green.
  // Coverage-gap variant: the guard this pins already exists, so the test passes as written.
  // Its bite was verified by deleting `if (trimmed)` from ChatWorkspace.send(), which made the
  // first `not.toHaveBeenCalled()` below fail with
  //   AssertionError: expected "vi.fn()" to not be called at all, but actually been called 1 times
  //   Received: 1st vi.fn() call: Array [ "" ]
  // The guard was then restored.
  it('does not submit a whitespace-only topic sent with Ctrl/Cmd+Enter', () => {
    const { onSubmit } = renderWorkspace()

    const input = screen.getByTestId('topic-input')
    typeTopic('   ')

    fireEvent.keyDown(input, { key: 'Enter', ctrlKey: true })
    expect(onSubmit).not.toHaveBeenCalled()

    // Cleared so the meta arm is judged on its own dispatch: without this the second
    // `not.toHaveBeenCalled()` merely re-reads the ctrl arm's state and a meta-key
    // regression would be invisible.
    onSubmit.mockClear()
    fireEvent.keyDown(input, { key: 'Enter', metaKey: true })
    expect(onSubmit).not.toHaveBeenCalled()

    // Control arm. Both negatives above also hold if Composer's onKeyDown is deleted outright,
    // which would pin nothing about `if (trimmed)`. This asserts the same key combination does
    // reach send() — and with the trimmed topic — so the silence above is the guard's doing.
    typeTopic('  Тема  ')
    fireEvent.keyDown(input, { key: 'Enter', ctrlKey: true })
    expect(onSubmit).toHaveBeenCalledTimes(1)
    expect(onSubmit).toHaveBeenCalledWith('Тема', EMPTY_PARAMETERS)
  })

  it('shows generated content and actual volumePages when completed', () => {
    renderWorkspace({ state: 'completed', content: '# Готовый текст', volumePages: 7 })

    // Anchored: '# Готовый текст' must arrive as a rendered heading, so the '#' is consumed and
    // the body's whole text is exactly the title — a substring match would pass on raw markdown.
    expect(screen.getByTestId('doc-body')).toHaveTextContent(/^Готовый текст$/)
    expect(screen.getByText('Доклад · 7 страниц · создан только что')).toBeInTheDocument()
  })

  it('shows error message when failed', () => {
    renderWorkspace({ state: 'failed', error: 'Не удалось создать запрос' })

    const errorBlock = screen.getByTestId('doc-error')
    expect(within(errorBlock).getByText('Не удалось создать запрос')).toBeInTheDocument()
    expect(within(errorBlock).getByRole('heading')).toHaveTextContent(
      /^Не удалось сгенерировать доклад$/,
    )
  })

  // Both reset buttons were unreachable by test and by locator — no data-testid, and nothing
  // asserted either one invokes onReset. Severing the onClick, or the onReset prop-drill above
  // it, was green across the whole suite. The failed panel is the one screen with no other exit.
  it('offers a way out of a completed generation', () => {
    const { onReset } = renderWorkspace({ state: 'completed', content: '# Готово', volumePages: 3 })

    fireEvent.click(screen.getByTestId('doc-reset'))

    expect(onReset).toHaveBeenCalledTimes(1)
  })

  it('offers a way out of a failed generation', () => {
    const { onReset } = renderWorkspace({ state: 'failed', error: 'Не удалось создать запрос' })

    fireEvent.click(screen.getByTestId('error-reset'))

    expect(onReset).toHaveBeenCalledTimes(1)
  })

  // The topic lives in this component's state, which useGeneration.reset() cannot reach, and the
  // workspace is not unmounted across a reset. So the new-request screen used to come back
  // holding the topic that was just generated, with the send button already enabled — one
  // keystroke re-bills the user for the document they already have. Unlike the double-Ctrl+Enter
  // case, this second submit is a separate gesture, so nothing about render ordering helps.
  it('comes back to an empty composer after a reset, not the topic just generated', () => {
    const { setState } = renderWorkspace()
    typeTopic('Влияние ИИ на образование')

    setState({ state: 'completed', content: '# Готово', volumePages: 3 })
    fireEvent.click(screen.getByTestId('doc-reset'))
    setState({ state: 'idle' })

    expect(screen.getByTestId('topic-input')).toHaveValue('')
    expect(screen.getByTestId('topic-send')).toBeDisabled()
  })
})
