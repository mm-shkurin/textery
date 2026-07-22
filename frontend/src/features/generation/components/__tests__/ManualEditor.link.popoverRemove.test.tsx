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
  // Both inputs trim to empty and must take the SAME `if (!trimmed)` remove-link
  // branch — the only difference is that a whitespace-only value proves the trim
  // happens. Parameterized so that sameness is structural, not two copies.
  it.each([
    ['an empty input', ''],
    ['a whitespace-only input (trims to empty)', '   '],
  ])('pressing Применить with %s removes the link but keeps the text', async (_label, value) => {
    const contentArea = await openLinkPopoverInsideExistingLink('https://old.example.com')

    fireEvent.change(screen.getByTestId('link-url-input'), { target: { value } })
    fireEvent.click(screen.getByTestId('link-apply'))

    expectLinkRemoved(contentArea)
  })
})
