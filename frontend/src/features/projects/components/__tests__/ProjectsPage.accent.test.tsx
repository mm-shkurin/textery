import { describe, expect, it, vi } from 'vitest'
import { screen, within } from '@testing-library/react'
import { mockFeed, pinClockTo, renderProjectsPage } from './feedTestHarness'
import { UNKNOWN_TYPE_PROJECT } from './projectFixtures'
import { ESSAY_PROJECT, SOCHINENIE_PROJECT } from './projectAccentFixtures'

// `GET /api/v1/projects` does not exist on the backend yet — this suite builds against a mock of
// it, never a live call.
vi.mock('../../api/projectsApi')

describe('ProjectsPage card accent for an unfamiliar document type', () => {
  // The clock is pinned because the card's date format branches on `getFullYear() !== now`, and
  // this block's fixture is dated 2026. Without this the suite green-passes only while the wall
  // clock agrees with the fixture.
  pinClockTo('2026-08-03T12:00:00.000Z')

  // The accent is asserted on the ANCESTOR of the badge, not on the badge itself: the stylesheet
  // colours the chip through `.project-card-accent-blue .project-card-type`, so the card carrying
  // the class is what decides whether the badge is tinted or renders as a transparent, unstyled
  // chip. Both halves are asserted — the fallback accent present, AND no other accent present —
  // because asserting only the first would pass on a card that somehow wore two accents, and the
  // point of the fallback is that exactly one tint is chosen.
  it('gives a project of an unknown wire type the blue fallback accent rather than no accent', async () => {
    mockFeed([UNKNOWN_TYPE_PROJECT], 1)

    renderProjectsPage()

    const card = await screen.findByTestId('project-card')

    expect(card).toHaveClass('project-card-accent-blue')
    expect(card).not.toHaveClass('project-card-accent-purple')
    expect(card).not.toHaveClass('project-card-accent-teal')
    expect(card).not.toHaveClass('project-card-accent-coral')
    expect(within(card).getByTestId('project-card-type')).toBeInTheDocument()
  })
})

// Both types in ONE case, on ONE feed: the defect was not "эссе had the wrong colour" but "эссе and
// сочинение had the SAME colour", and a claim about sameness cannot be made by two tests that each
// see one card. Rendering them side by side is also what the user does — the two sit in the same
// grid.
describe('ProjectsPage card accents distinguish эссе from сочинение', () => {
  pinClockTo('2026-08-03T12:00:00.000Z')

  it('tints эссе coral and сочинение teal rather than giving both the same accent', async () => {
    mockFeed([ESSAY_PROJECT, SOCHINENIE_PROJECT], 2)

    renderProjectsPage()

    const [essay, sochinenie] = await screen.findAllByTestId('project-card')

    expect(essay).toHaveClass('project-card-accent-coral')
    expect(essay).not.toHaveClass('project-card-accent-teal')
    expect(sochinenie).toHaveClass('project-card-accent-teal')
    expect(sochinenie).not.toHaveClass('project-card-accent-coral')
    // The badges name the two types, so a fixture swap cannot satisfy the assertions above.
    expect(within(essay).getByTestId('project-card-type')).toHaveTextContent('Эссе')
    expect(within(sochinenie).getByTestId('project-card-type')).toHaveTextContent('Сочинение')
  })
})
