import { describe, expect, it } from 'vitest'
import { render, screen } from '@testing-library/react'

import { LastActionPanel } from './LastActionPanel'
import type { TrainingUpdate } from '@/hooks/useTrainingStream'

const fakeEvent = (overrides: Partial<TrainingUpdate['last_action']> = {}): TrainingUpdate => ({
  generation: 5,
  current_sharpe: 0.1,
  best_sharpe: 0.2,
  balance: 10000,
  pnl: 0,
  win_rate: 0.5,
  progress: 0.1,
  action_distribution: { buy: 1, hold: 1, sell: 1 },
  cumulative_buys: 1,
  cumulative_sells: 1,
  last_action: {
    action: 'BUY',
    timestamp: '2026-05-14T00:00:00Z',
    execution_price: 100,
    size_percent: 50,
    position_before: 0,
    position_after: 0.5,
    notional_usd: 50,
    balance_before: 10000,
    balance_after: 9950,
    fee: 0.05,
    unrealized_pnl_after: 0,
    ...overrides,
  },
})

describe('LastActionPanel', () => {
  it('renders the panel heading', () => {
    render(<LastActionPanel event={null} />)
    expect(screen.getByRole('heading', { name: /last action/i })).toBeInTheDocument()
  })

  it('shows placeholder content when event is null', () => {
    render(<LastActionPanel event={null} />)
    expect(screen.getByTestId('last-action-empty')).toBeInTheDocument()
    expect(screen.queryByTestId('last-action-direction')).not.toBeInTheDocument()
  })

  it('renders BUY action with distinct visual marker when event is present', () => {
    render(<LastActionPanel event={fakeEvent({ action: 'BUY', execution_price: 105 })} />)
    expect(screen.getByTestId('last-action-direction')).toHaveAttribute('data-action', 'BUY')
    expect(screen.getByTestId('last-action-price')).toHaveTextContent('$105.00')
  })

  it('renders SELL action with distinct visual marker', () => {
    render(<LastActionPanel event={fakeEvent({ action: 'SELL', execution_price: 99 })} />)
    expect(screen.getByTestId('last-action-direction')).toHaveAttribute('data-action', 'SELL')
  })

  it('renders HOLD action with distinct visual marker', () => {
    render(<LastActionPanel event={fakeEvent({ action: 'HOLD' })} />)
    expect(screen.getByTestId('last-action-direction')).toHaveAttribute('data-action', 'HOLD')
  })
})
