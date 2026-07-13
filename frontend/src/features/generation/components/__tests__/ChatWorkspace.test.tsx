import { describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen } from '@testing-library/react'
import { ChatWorkspace } from '../ChatWorkspace'

describe('ChatWorkspace', () => {
  it('disables send button until topic is non-empty', () => {
    render(
      <ChatWorkspace
        documentTypeLabel="Доклад"
        state="idle"
        content={null}
        volumePages={null}
        error={null}
        onSubmit={vi.fn()}
        onReset={vi.fn()}
      />,
    )

    const send = screen.getByTestId('topic-send')
    expect(send).toBeDisabled()

    fireEvent.change(screen.getByTestId('topic-input'), { target: { value: 'Тема доклада' } })
    expect(send).toBeEnabled()
  })

  it('calls onSubmit with trimmed topic', () => {
    const onSubmit = vi.fn()
    render(
      <ChatWorkspace
        documentTypeLabel="Доклад"
        state="idle"
        content={null}
        volumePages={null}
        error={null}
        onSubmit={onSubmit}
        onReset={vi.fn()}
      />,
    )

    fireEvent.change(screen.getByTestId('topic-input'), { target: { value: '  Тема  ' } })
    fireEvent.click(screen.getByTestId('topic-send'))

    expect(onSubmit).toHaveBeenCalledWith('Тема')
  })

  it('shows generated content and actual volumePages when completed', () => {
    render(
      <ChatWorkspace
        documentTypeLabel="Доклад"
        state="completed"
        content="# Готовый текст"
        volumePages={7}
        error={null}
        onSubmit={vi.fn()}
        onReset={vi.fn()}
      />,
    )

    expect(screen.getByTestId('doc-body')).toHaveTextContent('Готовый текст')
    expect(screen.getByText(/7 страниц/)).toBeInTheDocument()
  })

  it('shows error message when failed', () => {
    render(
      <ChatWorkspace
        documentTypeLabel="Доклад"
        state="failed"
        content={null}
        volumePages={null}
        error="Не удалось создать запрос"
        onSubmit={vi.fn()}
        onReset={vi.fn()}
      />,
    )

    expect(screen.getByTestId('doc-error')).toHaveTextContent('Не удалось создать запрос')
  })
})
