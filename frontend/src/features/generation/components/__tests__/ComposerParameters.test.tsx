import { describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen } from '@testing-library/react'
import { Composer } from '../Composer'
import { topicFieldLabel } from '../../../../shared/documentTypes'
import {
  DEFAULT_VOLUME_PAGES,
  EMPTY_PARAMETERS,
  MAX_EXTRA_WISHES_LENGTH,
  MAX_REQUIREMENTS_LENGTH,
  MAX_VOLUME_PAGES,
  MIN_VOLUME_PAGES,
  type GenerationParameters,
} from '../../generationParameters'

function renderComposer(topic = 'Тема', parameters: GenerationParameters = EMPTY_PARAMETERS) {
  const setParameters = vi.fn()
  const onSend = vi.fn()
  render(
    <Composer
      topicLabel={topicFieldLabel('doklad')}
      topic={topic}
      setTopic={vi.fn()}
      parameters={parameters}
      setParameters={setParameters}
      onSend={onSend}
    />,
  )
  return { setParameters, onSend }
}

describe('the generation parameters the form collects', () => {
  // The gap this closes: the composer collected a topic and nothing else, while the client sent
  // a hardcoded 5 pages and no требования at all. Every field below is drawn in
  // mockups/desktop/04-generation-form.html and was never built.
  it('offers all three fields beside the topic', () => {
    renderComposer()

    expect(screen.getByTestId('requirements-input')).toBeInTheDocument()
    expect(screen.getByTestId('volume-input')).toBeInTheDocument()
    expect(screen.getByTestId('wishes-input')).toBeInTheDocument()
  })

  it('names each field for a screen reader', () => {
    renderComposer()

    // By accessible name, not by testid: a field labelled only by an adjacent heading is an
    // unlabelled box to anyone not looking at the screen, which is the defect the topic field's
    // own aria-labelledby exists to prevent.
    expect(screen.getByRole('textbox', { name: 'Требования' })).toBeInTheDocument()
    expect(screen.getByRole('spinbutton', { name: /Объём, страниц/ })).toBeInTheDocument()
    expect(screen.getByRole('textbox', { name: 'Дополнительные пожелания' })).toBeInTheDocument()
  })

  it('starts at the volume the mockup shows', () => {
    renderComposer()

    expect(screen.getByTestId('volume-input')).toHaveValue(DEFAULT_VOLUME_PAGES)
  })

  it('bounds the volume input at the range the server accepts', () => {
    renderComposer()

    const volume = screen.getByTestId('volume-input')
    expect(volume).toHaveAttribute('min', String(MIN_VOLUME_PAGES))
    expect(volume).toHaveAttribute('max', String(MAX_VOLUME_PAGES))
  })

  it('caps both text fields at the domain length limits', () => {
    renderComposer()

    // Mirrored from the domain so the keystroke is stopped rather than the request refused:
    // a 400 after three thousand characters is an answer the user cannot act on.
    expect(screen.getByTestId('requirements-input')).toHaveAttribute(
      'maxlength',
      String(MAX_REQUIREMENTS_LENGTH),
    )
    expect(screen.getByTestId('wishes-input')).toHaveAttribute(
      'maxlength',
      String(MAX_EXTRA_WISHES_LENGTH),
    )
  })

  it('reports each edit to the caller without losing the other fields', () => {
    const { setParameters } = renderComposer()

    fireEvent.change(screen.getByTestId('requirements-input'), {
      target: { value: 'Официально-деловой стиль' },
    })

    // The WHOLE object, not the one field: an onChange that emitted `{requirements}` alone would
    // silently reset the volume to undefined and send a request the server refuses.
    expect(setParameters).toHaveBeenCalledWith({
      ...EMPTY_PARAMETERS,
      requirements: 'Официально-деловой стиль',
    })
  })

  it('carries the volume as a number, not as the input string', () => {
    const { setParameters } = renderComposer()

    fireEvent.change(screen.getByTestId('volume-input'), { target: { value: '8' } })

    expect(setParameters).toHaveBeenCalledWith({ ...EMPTY_PARAMETERS, volumePages: 8 })
  })
})

describe('the send button and the required fields', () => {
  it('is enabled when the topic and the volume are both usable', () => {
    renderComposer('Тема')

    expect(screen.getByTestId('topic-send')).toBeEnabled()
  })

  it.each([
    ['above the maximum', MAX_VOLUME_PAGES + 1],
    ['below the minimum', MIN_VOLUME_PAGES - 1],
    ['a cleared input', Number.NaN],
    ['fractional', 2.5],
  ])('is disabled when the volume is %s', (_case, volumePages) => {
    // Without this the form submits a volume the server answers 400 for, on a screen with
    // nowhere to show that answer — the user sees the generation simply fail.
    renderComposer('Тема', { ...EMPTY_PARAMETERS, volumePages })

    expect(screen.getByTestId('topic-send')).toBeDisabled()
  })
})
