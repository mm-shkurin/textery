import { describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen } from '@testing-library/react'
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

    expect(screen.getByTestId('generation-breadcrumb')).toHaveTextContent('Доклад')
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

    expect(screen.getByTestId('generation-breadcrumb')).toHaveTextContent('Реферат')
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

    expect(onSubmit).toHaveBeenCalledWith('Тема')
  })

  it('shows generated content and actual volumePages when completed', () => {
    renderWorkspace({ state: 'completed', content: '# Готовый текст', volumePages: 7 })

    expect(screen.getByTestId('doc-body')).toHaveTextContent('Готовый текст')
    expect(screen.getByText(/7 страниц/)).toBeInTheDocument()
  })

  it('shows error message when failed', () => {
    renderWorkspace({ state: 'failed', error: 'Не удалось создать запрос' })

    expect(screen.getByTestId('doc-error')).toHaveTextContent('Не удалось создать запрос')
  })
})
