import { describe, expect, it, vi } from 'vitest'
import { fireEvent, screen } from '@testing-library/react'
import {
  expectSoleLink,
  openLinkPopover,
  openLinkPopoverInsideExistingLink,
} from './ManualEditor.link.testSupport'
import { LINK_INVALID_MESSAGE } from '../LinkPopover'

vi.mock('../../api/documentApi')

describe('ManualEditor link popover — keyboard and click-outside', () => {
  // RED 2026-07-21 (green-frontend-popover-contract owns the fix): the URL input
  // has no onKeyDown, so Enter does nothing. Actual: expected the anchor set to
  // have length 1 but got 0.
  it.skip('pressing Enter in the URL field applies the link, same as clicking Применить', async () => {
    const contentArea = await openLinkPopover()

    const input = screen.getByTestId('link-url-input')
    fireEvent.change(input, { target: { value: 'https://example.com' } })
    fireEvent.keyDown(input, { key: 'Enter' })

    expectSoleLink(contentArea, 'https://example.com')
  })

  // RED 2026-07-21: no Escape handler, so the popover stays mounted. Actual:
  // expected document not to contain element, found the popover <div>.
  it.skip('pressing Escape cancels: the popover closes and an existing link is left untouched', async () => {
    const contentArea = await openLinkPopoverInsideExistingLink('https://keep.example.com')

    fireEvent.keyDown(screen.getByTestId('link-url-input'), { key: 'Escape' })

    expect(screen.queryByTestId('link-popover')).not.toBeInTheDocument()
    const anchors = contentArea.querySelectorAll('a')
    expect(anchors).toHaveLength(1)
    expect(anchors[0].getAttribute('href')).toBe('https://keep.example.com')
    expect(contentArea.textContent).toBe('hello world')
  })

  // RED 2026-07-21: no click-outside listener, so the popover neither closes nor
  // applies. Actual: expected document not to contain element, found the popover.
  it.skip('clicking outside the popover closes it and applies the captured range', async () => {
    const contentArea = await openLinkPopover()

    fireEvent.change(screen.getByTestId('link-url-input'), {
      target: { value: 'https://example.com' },
    })
    fireEvent.mouseDown(document.body)

    expect(screen.queryByTestId('link-popover')).not.toBeInTheDocument()
    expectSoleLink(contentArea, 'https://example.com')
  })

  // RED 2026-07-21 (ADR tension 2, leaning (b): close on success, stay-open-with-
  // alert on rejection): no click-outside handler runs apply(), so no alert
  // appears. Actual: unable to find an accessible element with the role "alert".
  it.skip('clicking outside with a rejected href keeps the popover open and shows the inline alert rather than swallowing the rejection', async () => {
    await openLinkPopover()

    fireEvent.change(screen.getByTestId('link-url-input'), {
      target: { value: 'javascript:alert(1)' },
    })
    fireEvent.mouseDown(document.body)

    expect(screen.getByTestId('link-popover')).toBeInTheDocument()
    expect(screen.getByRole('alert')).toHaveTextContent(LINK_INVALID_MESSAGE)
  })
})
