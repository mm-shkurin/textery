import { describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen, within } from '@testing-library/react'
import { ChatWorkspace } from '../ChatWorkspace'
import type { ComponentProps } from 'react'

type WorkspaceProps = ComponentProps<typeof ChatWorkspace>

function renderWorkspace(overrides: Partial<WorkspaceProps> = {}) {
  const onSubmit = vi.fn()
  const onReset = vi.fn()
  render(
    <ChatWorkspace
      documentType="doklad"
      documentTypeLabel="Доклад"
      state="idle"
      content={null}
      volumePages={null}
      error={null}
      onSubmit={onSubmit}
      onReset={onReset}
      {...overrides}
    />,
  )
  return { onSubmit, onReset }
}

describe('ChatWorkspace', () => {
  // The heading slot is owned by two different mockups: before anything is submitted it is
  // mockup 04's breadcrumb + title, and from the first generation onward it is mockups 05-07's
  // status badge. Both arms were previously unasserted — deleting the idle branch outright left
  // the whole suite green.
  it('introduces the idle composer with the breadcrumb heading and no status badge', () => {
    renderWorkspace()

    expect(screen.getByTestId('generation-breadcrumb')).toHaveTextContent(/^Доклад$/)
    expect(screen.getByText('Новая генерация')).toBeInTheDocument()
    expect(screen.queryByText('Новый запрос')).not.toBeInTheDocument()
  })

  it('replaces the heading with the run status badge once a generation exists', () => {
    renderWorkspace({ state: 'pending' })

    expect(screen.getByText('В обработке')).toBeInTheDocument()
    expect(screen.queryByTestId('generation-breadcrumb')).not.toBeInTheDocument()
    expect(screen.queryByText('Новая генерация')).not.toBeInTheDocument()
  })

  // documentType and documentTypeLabel arrive as independent props, so a caller can pair a
  // 'referat' id with a 'Доклад' label and put two different type names on one screen — the
  // breadcrumb renders the label, the composer heading renders topicFieldLabel(documentType).
  // DocumentGenerationFlow derives them consistently today; this pins the contract at the
  // component boundary so a future caller cannot silently re-open the bug.
  it('names one and the same document type in the breadcrumb and the topic field', () => {
    renderWorkspace({ documentType: 'referat', documentTypeLabel: 'Реферат' })

    expect(screen.getByTestId('generation-breadcrumb')).toHaveTextContent(/^Реферат$/)
    expect(screen.getByRole('textbox', { name: 'Тема реферата' })).toBeInTheDocument()
  })

  it('disables send button until topic is non-empty', () => {
    renderWorkspace()

    const send = screen.getByTestId('topic-send')
    expect(send).toBeDisabled()

    fireEvent.change(screen.getByTestId('topic-input'), { target: { value: 'Тема доклада' } })
    expect(send).toBeEnabled()
  })

  it('calls onSubmit with trimmed topic', () => {
    const { onSubmit } = renderWorkspace()

    fireEvent.change(screen.getByTestId('topic-input'), { target: { value: '  Тема  ' } })
    fireEvent.click(screen.getByTestId('topic-send'))

    expect(onSubmit).toHaveBeenCalledTimes(1)
    expect(onSubmit).toHaveBeenCalledWith('Тема')
  })

  // The send button is disabled while the topic is blank, but Composer's textarea fires onSend on
  // Ctrl/Cmd+Enter with no disabled guard — so a whitespace-only topic reaches send() and the
  // `if (trimmed)` there is the only thing stopping an empty-topic POST (backend 422). That false
  // branch was the file's single uncovered branch: deleting the `if` left the whole suite green.
  // RED, coverage-gap variant: the guard this pins already exists, so the test passes as written.
  // Its bite was verified by deleting `if (trimmed)` from ChatWorkspace.send(), which produced
  //   AssertionError: expected "vi.fn()" to not be called at all, but actually been called 1 times
  //   Received: 1st vi.fn() call: Array [ "" ]   (ChatWorkspace.test.tsx:90:26)
  // The guard was then restored; green-frontend removes this marker only.
  it.skip('does not submit a whitespace-only topic sent with Ctrl/Cmd+Enter', () => {
    const { onSubmit } = renderWorkspace()

    const input = screen.getByTestId('topic-input')
    fireEvent.change(input, { target: { value: '   ' } })

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
    fireEvent.change(input, { target: { value: '  Тема  ' } })
    fireEvent.keyDown(input, { key: 'Enter', ctrlKey: true })
    expect(onSubmit).toHaveBeenCalledTimes(1)
    expect(onSubmit).toHaveBeenCalledWith('Тема')
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
})
