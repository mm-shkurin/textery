import { describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen } from '@testing-library/react'
import { Composer, MAX_TOPIC_LENGTH } from '../Composer'
import { topicFieldLabel } from '../../../../shared/copy/documentTypeCopy'
import { EMPTY_PARAMETERS, type GenerationParameters } from '../../generationParameters'

function renderComposer(
  topic: string,
  topicLabel = topicFieldLabel('doklad'),
  parameters: GenerationParameters = EMPTY_PARAMETERS,
) {
  const setTopic = vi.fn()
  const setParameters = vi.fn()
  const onSend = vi.fn()
  const view = render(
    <Composer
      topicLabel={topicLabel}
      topic={topic}
      setTopic={setTopic}
      parameters={parameters}
      setParameters={setParameters}
      onSend={onSend}
    />,
  )
  return { ...view, setTopic, setParameters, onSend }
}

describe('Composer', () => {
  // The field is named by the visible heading rather than a <label>, so the association is the
  // only thing standing between a screen-reader user and an unlabelled text box.
  it('gives the topic field the visible heading as its accessible name', () => {
    renderComposer('')

    expect(screen.getByRole('textbox', { name: 'Тема доклада' })).toBeInTheDocument()
  })

  // The heading used to be a hardcoded 'Тема доклада' lifted from the mockup, sitting directly
  // under a breadcrumb that renders the type the user actually picked — so any non-доклад type
  // showed two different type names on one screen, and the screen reader announced the wrong one.
  it('names the field after the type the user picked, not the default', () => {
    renderComposer('', topicFieldLabel('referat'))

    expect(screen.getByRole('textbox', { name: 'Тема реферата' })).toBeInTheDocument()
  })

  // The required asterisk used to be a `::after` on the same heading. jsdom applies no CSS, so
  // the test above stayed green while a real browser — which folds generated content into the
  // accessible-name computation — announced 'Тема доклада *'. Keeping the marker in markup and
  // aria-hidden is what makes the assertion above true outside jsdom too.
  // Every required field, not the first one found: there are two now (тема and объём), and a
  // `getByText` over the shared class throws on the second rather than checking it — the volume
  // field's marker could have shipped announced with nothing red.
  it('keeps every required marker out of the accessible name', () => {
    const { container } = renderComposer('')

    const markers = container.querySelectorAll('.composer-required-marker')
    expect(markers).toHaveLength(2)
    markers.forEach((marker) => expect(marker).toHaveAttribute('aria-hidden', 'true'))
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
