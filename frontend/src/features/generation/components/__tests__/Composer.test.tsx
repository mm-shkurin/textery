import { describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen } from '@testing-library/react'
import { Composer, MAX_TOPIC_LENGTH } from '../Composer'

function renderComposer(topic: string) {
  const setTopic = vi.fn()
  const onSend = vi.fn()
  render(<Composer topic={topic} setTopic={setTopic} onSend={onSend} />)
  return { setTopic, onSend }
}

describe('Composer', () => {
  // The field is named by the visible heading rather than a <label>, so the association is the
  // only thing standing between a screen-reader user and an unlabelled text box.
  it('gives the topic field the visible heading as its accessible name', () => {
    renderComposer('')

    expect(screen.getByRole('textbox', { name: 'Тема доклада' })).toBeInTheDocument()
  })

  it('reports every keystroke to the caller', () => {
    const { setTopic } = renderComposer('')

    fireEvent.change(screen.getByTestId('topic-input'), { target: { value: 'ИИ в образовании' } })

    expect(setTopic).toHaveBeenCalledWith('ИИ в образовании')
  })

  // A generation request with nothing to generate from is a wasted round trip and a confusing
  // failure, so the button is the guard — whitespace does not count as a topic.
  it('refuses to send while the topic is empty or whitespace', () => {
    renderComposer('   ')

    expect(screen.getByTestId('topic-send')).toBeDisabled()
  })

  it('sends on click once the topic has content', () => {
    const { onSend } = renderComposer('Доклад про Рим')

    fireEvent.click(screen.getByTestId('topic-send'))

    expect(onSend).toHaveBeenCalledTimes(1)
  })

  it('sends on the ctrl+enter shortcut', () => {
    const { onSend } = renderComposer('Доклад про Рим')

    fireEvent.keyDown(screen.getByTestId('topic-input'), { key: 'Enter', ctrlKey: true })

    expect(onSend).toHaveBeenCalledTimes(1)
  })

  it('sends on the cmd+enter shortcut', () => {
    const { onSend } = renderComposer('Доклад про Рим')

    fireEvent.keyDown(screen.getByTestId('topic-input'), { key: 'Enter', metaKey: true })

    expect(onSend).toHaveBeenCalledTimes(1)
  })

  // A bare Enter has to stay a newline: the field is a textarea because topics run to a sentence
  // or two, and submitting on Enter would truncate them mid-thought.
  it('leaves a bare enter to insert a newline instead of submitting', () => {
    const { onSend } = renderComposer('Доклад про Рим')

    fireEvent.keyDown(screen.getByTestId('topic-input'), { key: 'Enter' })

    expect(onSend).not.toHaveBeenCalled()
  })

  it('caps the topic at the documented length rather than letting the request fail server-side', () => {
    renderComposer('')

    expect(screen.getByTestId('topic-input')).toHaveAttribute('maxLength', String(MAX_TOPIC_LENGTH))
  })
})
