import { describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen } from '@testing-library/react'
import { Composer } from '../Composer'
import { topicFieldLabel } from '../../../../shared/copy/documentTypeCopy'
import { EMPTY_PARAMETERS, type GenerationParameters } from '../../utils/generationParameters'

function renderComposer(parameters: GenerationParameters = EMPTY_PARAMETERS) {
  const setParameters = vi.fn()
  render(
    <Composer
      topicLabel={topicFieldLabel('doklad')}
      documentType="doklad"
      topic="Тема"
      setTopic={vi.fn()}
      parameters={parameters}
      setParameters={setParameters}
      onSend={vi.fn()}
    />,
  )
  return { setParameters }
}

describe('Composer — «выбрать стиль текста»', () => {
  it('starts with no register chosen', () => {
    renderComposer()

    // NOT preselected to «научный». A default would send a register on every untouched form,
    // recording a choice the user never made — and «не выбран» is a real, different instruction to
    // the model rather than a missing value.
    expect(screen.getByTestId('style-select')).toHaveValue('')
  })

  it('offers the three registers the server accepts', () => {
    renderComposer()

    const values = Array.from(screen.getByTestId('style-select').querySelectorAll('option')).map(
      (option) => option.getAttribute('value'),
    )

    // The wire vocabulary, exactly: the server validates against these Cyrillic strings, so a
    // fourth option here is a 422 the user cannot explain.
    expect(values).toEqual(['', 'научный', 'публицистический', 'художественный'])
  })

  it('reports the picked register as the wire value', () => {
    const { setParameters } = renderComposer()

    fireEvent.change(screen.getByTestId('style-select'), { target: { value: 'художественный' } })

    expect(setParameters).toHaveBeenCalledWith(
      expect.objectContaining({ textStyle: 'художественный' }),
    )
  })

  it('leaves the other parameters alone when the register changes', () => {
    const { setParameters } = renderComposer({
      ...EMPTY_PARAMETERS,
      volumePages: 7,
      requirements: 'Ссылки на источники',
    })

    fireEvent.change(screen.getByTestId('style-select'), { target: { value: 'научный' } })

    // The picker writes into the SAME parameters object the volume and the requirements live in.
    // Replacing it wholesale would silently reset the two fields the user already filled in.
    expect(setParameters).toHaveBeenCalledWith(
      expect.objectContaining({ volumePages: 7, requirements: 'Ссылки на источники' }),
    )
  })

  it('explains the chosen register rather than only naming it', () => {
    renderComposer({ ...EMPTY_PARAMETERS, textStyle: 'публицистический' })

    // The labels alone leave a user guessing at the difference between публицистический and
    // художественный; the hint is the only place that difference is stated.
    expect(screen.getByTestId('style-hint')).toHaveTextContent('Живая аргументация')
  })

  it('explains nothing while no register is chosen', () => {
    renderComposer()

    expect(screen.queryByTestId('style-hint')).toBeNull()
  })
})
