import { describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { LandingExamples } from '../LandingExamples'
import { LANDING_EXAMPLES } from '../../utils/landingExamples'

describe('LandingExamples — «посмотреть примеры готовых работ»', () => {
  it('shows one example per document type', () => {
    render(<LandingExamples />)

    // Four cards, one per type the product offers: a section that showed only доклад would leave
    // a visitor who needs an эссе with no evidence at all.
    expect(screen.getAllByTestId('landing-example')).toHaveLength(LANDING_EXAMPLES.length)
  })

  it('shows the text itself, not only the titles', () => {
    render(<LandingExamples />)

    // The excerpt is what does the selling. A section naming four types and showing none of them
    // asks the visitor to take the product's word for its output quality on the one screen where
    // that is the only open question.
    expect(screen.getByText(LANDING_EXAMPLES[0].excerpt)).toBeInTheDocument()
  })

  it('opens the first example so the section is never a row of closed boxes', () => {
    render(<LandingExamples />)

    expect(screen.getAllByTestId('landing-example')[0]).toHaveAttribute('open')
  })

  it('closes the previous example when another is opened', async () => {
    render(<LandingExamples />)
    const [first, second] = screen.getAllByTestId('landing-example')

    // `<details>` opens itself on click; the accordion behaviour is what the component adds.
    fireEvent.click(second.querySelector('summary')!)

    // Awaited, because `toggle` is queued as a task rather than dispatched synchronously — the
    // element opens itself immediately and the component hears about it on the next turn.
    //
    // Four expanded cards turn the section into a wall of body text, and the point is a sample
    // rather than the whole document.
    await waitFor(() => expect(first).not.toHaveAttribute('open'))
    expect(second).toHaveAttribute('open')
  })

  it('closes the open example when its own summary is pressed again', async () => {
    render(<LandingExamples />)
    const [first] = screen.getAllByTestId('landing-example')

    fireEvent.click(first.querySelector('summary')!)

    // The accordion must not trap the visitor with one card permanently open: pressing the open
    // card is the only way to collapse the section back to its four headings.
    await waitFor(() => expect(first).not.toHaveAttribute('open'))
  })

  it('sends a convinced visitor to the same place every other section does', () => {
    const onPrimaryCtaClick = vi.fn()
    render(<LandingExamples onPrimaryCtaClick={onPrimaryCtaClick} />)

    fireEvent.click(screen.getByTestId('examples-primary-cta-button'))

    expect(onPrimaryCtaClick).toHaveBeenCalledTimes(1)
  })
})
