import { describe, expect, it, vi } from 'vitest'
import { fireEvent, screen } from '@testing-library/react'
import { renderEditorWithDocumentCreated, selectRange } from './ManualEditor.testSupport'

vi.mock('../../api/documentApi')

describe('ManualEditor formatting toolbar', () => {
  it.each([
    {
      name: 'bold',
      testId: 'toolbar-bold',
      tag: 'strong',
      text: 'hello world',
      end: 5,
      expected: '<strong>hello</strong> world',
    },
    {
      name: 'strikethrough',
      testId: 'toolbar-strike',
      tag: 's',
      text: 'hello world',
      end: 5,
      expected: '<s>hello</s> world',
    },
    {
      name: 'underline',
      testId: 'toolbar-underline',
      tag: 'u',
      text: 'hello world',
      end: 5,
      expected: '<u>hello</u> world',
    },
  ])(
    'applying $name to selected text wraps it in <$tag> and marks the $name button active',
    async ({ testId, text, end, expected }) => {
      await renderEditorWithDocumentCreated()

      const contentArea = screen.getByTestId('editor-content-area')
      expect(contentArea).toHaveAttribute('contenteditable', 'true')

      contentArea.textContent = text
      fireEvent.input(contentArea)

      const textNode = contentArea.firstChild as Node
      selectRange(textNode, 0, end)
      fireEvent.select(contentArea)

      const button = screen.getByTestId(testId)
      fireEvent.click(button)

      expect(contentArea.innerHTML).toBe(expected)
      expect(button).toHaveAttribute('aria-pressed', 'true')
    },
  )

  it('moving the cursor from bold text to non-bold text deactivates the bold toolbar button', async () => {
    await renderEditorWithDocumentCreated()

    const contentArea = screen.getByTestId('editor-content-area')
    contentArea.textContent = 'bold plain'
    fireEvent.input(contentArea)

    const initialTextNode = contentArea.firstChild as Node
    selectRange(initialTextNode, 0, 4)
    fireEvent.select(contentArea)

    const boldButton = screen.getByTestId('toolbar-bold')
    fireEvent.click(boldButton)

    expect(contentArea.innerHTML).toBe('<strong>bold</strong> plain')
    expect(boldButton).toHaveAttribute('aria-pressed', 'true')

    const plainTextNode = contentArea.lastChild as Node
    selectRange(plainTextNode, 1, 1)
    fireEvent.select(contentArea)

    expect(boldButton).toHaveAttribute('aria-pressed', 'false')
    const italicButton = screen.getByLabelText('Курсив')
    expect(italicButton).toHaveAttribute('aria-pressed', 'false')
  })

  it.each([
    { name: 'strikethrough', testId: 'toolbar-strike', text: 'struck plain', markLen: 6, tag: 's' },
    { name: 'underline', testId: 'toolbar-underline', text: 'under plain', markLen: 5, tag: 'u' },
  ])(
    'moving the cursor from $name text to non-$name text deactivates the $name toolbar button',
    async ({ testId, text, markLen, tag }) => {
      await renderEditorWithDocumentCreated()

      const contentArea = screen.getByTestId('editor-content-area')
      contentArea.textContent = text
      fireEvent.input(contentArea)

      const initialTextNode = contentArea.firstChild as Node
      selectRange(initialTextNode, 0, markLen)
      fireEvent.select(contentArea)

      const button = screen.getByTestId(testId)
      fireEvent.click(button)

      expect(contentArea.innerHTML).toBe(
        `<${tag}>${text.slice(0, markLen)}</${tag}>${text.slice(markLen)}`,
      )
      expect(button).toHaveAttribute('aria-pressed', 'true')

      const plainTextNode = contentArea.lastChild as Node
      selectRange(plainTextNode, 1, 1)
      fireEvent.select(contentArea)

      expect(button).toHaveAttribute('aria-pressed', 'false')
    },
  )
})
