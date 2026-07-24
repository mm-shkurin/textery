import { describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen } from '@testing-library/react'
import { LandingHero } from '../LandingHero'

describe('LandingHero', () => {
  it('names the page with a single top-level heading', () => {
    render(<LandingHero />)

    expect(screen.getByTestId('hero-heading')).toHaveTextContent(
      'Textery — самая быстрая нейросеть для докладов',
    )
  })

  // The form's default action would reload the page and throw away whatever was typed; the
  // handler exists to stop that, so a submit must reach the caller instead of the browser.
  it('hands a submitted prompt to the caller without reloading the page', () => {
    const onPromptSubmit = vi.fn()
    render(<LandingHero onPromptSubmit={onPromptSubmit} />)

    fireEvent.click(screen.getByTestId('hero-generate-button'))

    expect(onPromptSubmit).toHaveBeenCalledTimes(1)
  })

  // The prop is optional, and the hero renders on a route that may not supply it. Submitting
  // there must be inert, not a crash on `undefined()`.
  it('survives a submit when no caller is listening', () => {
    render(<LandingHero />)

    expect(() => fireEvent.click(screen.getByTestId('hero-generate-button'))).not.toThrow()
  })

  it('labels the prompt field for a screen reader that never sees the placeholder', () => {
    render(<LandingHero />)

    expect(screen.getByRole('textbox', { name: 'Тема документа' })).toBeInTheDocument()
  })

  // Decorative ornaments: announced, they are four meaningless images between the heading and
  // the field. Hidden and empty-alt, a screen reader skips straight to the content.
  it('hides its decorative glass ornaments from assistive technology', () => {
    const { container } = render(<LandingHero />)

    const images = container.querySelectorAll('.hero-glass img')
    expect(images).toHaveLength(4)
    images.forEach((image) => {
      expect(image).toHaveAttribute('alt', '')
      expect(image.closest('[aria-hidden="true"]')).not.toBeNull()
    })
  })
})
