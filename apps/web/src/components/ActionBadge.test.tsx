import { describe, expect, it } from 'vitest'
import { render, screen } from '@testing-library/react'

import { ActionBadge } from './ActionBadge'

describe('ActionBadge', () => {
  it('renders BUY with data-action="BUY"', () => {
    render(<ActionBadge action="BUY" />)
    const badge = screen.getByText('BUY')
    expect(badge).toHaveAttribute('data-action', 'BUY')
  })

  it('renders SELL with data-action="SELL"', () => {
    render(<ActionBadge action="SELL" />)
    expect(screen.getByText('SELL')).toHaveAttribute('data-action', 'SELL')
  })

  it('renders HOLD with data-action="HOLD"', () => {
    render(<ActionBadge action="HOLD" />)
    expect(screen.getByText('HOLD')).toHaveAttribute('data-action', 'HOLD')
  })

  it('uses different variant attribute per action so styling is distinct', () => {
    const { container, rerender } = render(<ActionBadge action="BUY" />)
    const buyVariant = container.querySelector('[data-action="BUY"]')?.getAttribute('data-variant')
    rerender(<ActionBadge action="SELL" />)
    const sellVariant = container.querySelector('[data-action="SELL"]')?.getAttribute('data-variant')
    rerender(<ActionBadge action="HOLD" />)
    const holdVariant = container.querySelector('[data-action="HOLD"]')?.getAttribute('data-variant')
    expect(buyVariant).not.toBe(sellVariant)
    expect(buyVariant).not.toBe(holdVariant)
    expect(sellVariant).not.toBe(holdVariant)
  })
})
