import { describe, expect, it, vi } from 'vitest'
import { fireEvent, screen } from '@testing-library/react'
import { selectRange } from './ManualEditor.testSupport'
import {
  expectSoleLink,
  openLinkPopover,
  openLinkPopoverInsideExistingLink,
} from './ManualEditor.link.testSupport'

vi.mock('../../api/documentApi')

describe('ManualEditor link popover — captured range contract', () => {
  // RED 2026-07-21 (green-frontend-popover-contract owns the fix): LinkPopover
  // opens with useState('') — the field never prefills from the anchor under the
  // caret. Actual: expected '' to be 'https://old.example.com'.
  it('opening with the caret inside an existing link prefills the field with that href and Применить replaces it in place', async () => {
    const contentArea = await openLinkPopoverInsideExistingLink('https://old.example.com')

    const input = screen.getByTestId('link-url-input') as HTMLInputElement
    expect(input.value).toBe('https://old.example.com')

    fireEvent.change(input, { target: { value: 'https://new.example.com' } })
    fireEvent.click(screen.getByTestId('link-apply'))

    const anchors = contentArea.querySelectorAll('a')
    expect(anchors).toHaveLength(1)
    expect(anchors[0].getAttribute('href')).toBe('https://new.example.com')
  })

  // RED 2026-07-21: apply() runs on the live editor selection, so a caret moved
  // while the popover is open steals the target. No captured range exists yet.
  // Actual: expected the anchor set to have length 1 but got 0.
  it('Применить acts on the range captured when the popover opened, not the caret moved elsewhere while it was open', async () => {
    const contentArea = await openLinkPopover()

    selectRange(contentArea.firstChild as Node, 8, 8)
    fireEvent.select(contentArea)

    fireEvent.change(screen.getByTestId('link-url-input'), {
      target: { value: 'https://example.com' },
    })
    fireEvent.click(screen.getByTestId('link-apply'))

    expectSoleLink(contentArea, 'https://example.com')
  })

  // RED 2026-07-21: with no captured range, the retry after a rejection also
  // fires on the live (drifted) selection. Actual: expected the anchor set to
  // have length 1 but got 0.
  it('a rejected apply keeps the captured range, so the corrected retry still lands on the originally selected text', async () => {
    const contentArea = await openLinkPopover()

    fireEvent.change(screen.getByTestId('link-url-input'), {
      target: { value: 'javascript:alert(1)' },
    })
    fireEvent.click(screen.getByTestId('link-apply'))

    selectRange(contentArea.firstChild as Node, 8, 8)
    fireEvent.select(contentArea)

    fireEvent.change(screen.getByTestId('link-url-input'), {
      target: { value: 'https://example.com' },
    })
    fireEvent.click(screen.getByTestId('link-apply'))

    expectSoleLink(contentArea, 'https://example.com')
  })
})
