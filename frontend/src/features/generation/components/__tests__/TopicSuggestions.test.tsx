import { describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen } from '@testing-library/react'
import { Composer } from '../Composer'
import { topicFieldLabel } from '../../../../shared/copy/documentTypeCopy'
import { EMPTY_PARAMETERS } from '../../utils/generationParameters'
import { suggestionsFor } from '../../utils/topicSuggestions'
import type { DocumentType } from '../../../../shared/domain/documentTypes'

function renderComposer(topic = '', documentType: DocumentType = 'doklad') {
  const setTopic = vi.fn()
  render(
    <Composer
      topicLabel={topicFieldLabel(documentType)}
      documentType={documentType}
      topic={topic}
      setTopic={setTopic}
      parameters={EMPTY_PARAMETERS}
      setParameters={vi.fn()}
      onSend={vi.fn()}
    />,
  )
  return { setTopic }
}

describe('Composer — «увидеть примеры запросов»', () => {
  it('offers examples while the topic field is empty', () => {
    renderComposer('')

    // The examples are a way INTO the field, shown to a visitor who has an assignment in mind but
    // not a sentence — which is exactly the state an empty composer leaves them in.
    expect(screen.getByTestId('topic-suggestions')).toBeInTheDocument()
  })

  it('hides them once the user has written something of their own', () => {
    renderComposer('Моя собственная тема')

    // A click that replaced text somebody just typed would be a destructive surprise from a
    // control that looks like a hint — and there is no undo on a textarea they did not focus.
    expect(screen.queryByTestId('topic-suggestions')).toBeNull()
  })

  it('fills the topic field with the example that was pressed', () => {
    const { setTopic } = renderComposer('')
    const [first] = suggestionsFor('doklad')

    fireEvent.click(screen.getAllByTestId('topic-suggestion')[0])

    expect(setTopic).toHaveBeenCalledWith(first)
  })

  it('offers examples written for the type that was picked', () => {
    renderComposer('', 'sochinenie')

    const shown = screen.getAllByTestId('topic-suggestion').map((button) => button.textContent)

    // Per type, not one shared list: a topic that makes a good реферат makes a poor сочинение, and
    // a single list would show three quarters of its suggestions to the wrong screen.
    expect(shown).toEqual([...suggestionsFor('sochinenie')])
  })

  it('offers real buttons rather than decorative pills', () => {
    renderComposer('')

    // A <div> with an onClick is unreachable by keyboard and announced as nothing, and being
    // pressed is this control's entire purpose.
    for (const suggestion of screen.getAllByTestId('topic-suggestion')) {
      expect(suggestion.tagName).toBe('BUTTON')
    }
  })
})

describe('suggestionsFor', () => {
  it('answers an empty list for a type it has never heard of', () => {
    // The server owns the type vocabulary and can add one before this table does. An undefined
    // here would reach `.length` in the component and blank the whole composer.
    expect(suggestionsFor('коллоквиум' as DocumentType)).toEqual([])
  })
})
