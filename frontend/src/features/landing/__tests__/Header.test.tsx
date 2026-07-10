import { describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen } from '@testing-library/react'
import { Header } from '../components/Header'

describe('Header', () => {
  it('calls onPrimaryCtaClick when the CTA button is clicked', () => {
    const onPrimaryCtaClick = vi.fn()
    render(<Header onPrimaryCtaClick={onPrimaryCtaClick} />)

    fireEvent.click(screen.getByTestId('header-primary-cta-button'))

    expect(onPrimaryCtaClick).toHaveBeenCalledTimes(1)
  })

  it('renders without a handler without throwing', () => {
    render(<Header />)

    expect(() => fireEvent.click(screen.getByTestId('header-primary-cta-button'))).not.toThrow()
  })
})
