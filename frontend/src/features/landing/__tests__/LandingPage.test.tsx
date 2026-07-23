import { describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen } from '@testing-library/react'

import { LandingPage } from '../components/LandingPage'

describe('LandingPage', () => {
  it('should display the hero heading', () => {
    render(<LandingPage />)

    // toHaveTextContent does a substring `includes()` check (see jest-dom matchers-*.js
    // `matches()`), not exact equality -- asserting on `.textContent` with `toBe` instead
    // so a partial-text render (e.g. missing a word) fails the test.
    expect(screen.getByTestId('hero-heading').textContent).toBe(
      'Textery — самая быстрая нейросеть для докладов',
    )
  })

  it('calls onPrimaryCtaClick when the header CTA is clicked', () => {
    const onPrimaryCtaClick = vi.fn()
    render(<LandingPage onPrimaryCtaClick={onPrimaryCtaClick} />)

    fireEvent.click(screen.getByTestId('header-primary-cta-button'))

    expect(onPrimaryCtaClick).toHaveBeenCalledTimes(1)
  })

  it('calls onPrimaryCtaClick when the features-section CTA is clicked', () => {
    const onPrimaryCtaClick = vi.fn()
    render(<LandingPage onPrimaryCtaClick={onPrimaryCtaClick} />)

    fireEvent.click(screen.getByTestId('features-primary-cta-button'))

    expect(onPrimaryCtaClick).toHaveBeenCalledTimes(1)
  })
})
