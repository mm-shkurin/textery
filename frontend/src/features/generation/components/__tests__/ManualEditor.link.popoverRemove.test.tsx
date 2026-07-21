import { describe, it, vi } from 'vitest'
import { fireEvent, screen } from '@testing-library/react'
import {
  expectLinkRemoved,
  openLinkPopoverInsideExistingLink,
} from './ManualEditor.link.testSupport'

vi.mock('../../api/documentApi')

// Characterization (2026-07-21, red-frontend-coverage-empty-apply, Story 5 / 7.9):
// pins LinkPopover.tsx:37-46 — the empty/whitespace-input apply branch that
// removes the link mark. Behaviour already implemented, so these stay LIVE (no
// skip): they cover the `if (!trimmed)` true-branch, which no other test takes.
describe('ManualEditor link popover — clearing the field removes the link', () => {
  it('clearing the input to empty and pressing Применить removes the link but keeps the text', async () => {
    const contentArea = await openLinkPopoverInsideExistingLink('https://old.example.com')

    fireEvent.change(screen.getByTestId('link-url-input'), { target: { value: '' } })
    fireEvent.click(screen.getByTestId('link-apply'))

    expectLinkRemoved(contentArea)
  })

  it('a whitespace-only input trims to empty and takes the same remove-link branch', async () => {
    const contentArea = await openLinkPopoverInsideExistingLink('https://old.example.com')

    fireEvent.change(screen.getByTestId('link-url-input'), { target: { value: '   ' } })
    fireEvent.click(screen.getByTestId('link-apply'))

    expectLinkRemoved(contentArea)
  })
})
