import { describe, expect, it } from 'vitest'
import { render, screen } from '@testing-library/react'

import { LastActionPanel } from './LastActionPanel'
import type { TrainingUpdate } from '@/hooks/useTrainingStream'

const fakeEvent = (overrides: Partial<NonNullable<TrainingUpdate['last_transaction']>> = {}): TrainingUpdate => ({
  generation: 5,
  training_sharpe: 0.1,
  evaluation_sharpe: 0.1,
  best_evaluation_sharpe: 0.2,
  balance: 10000,
  pnl: 0,
  trade_win_rate: 0.5,
  progress: 0.1,
  transaction_distribution: { buy: 1, sell: 1, no_transaction: 1 },
  cumulative_buys: 1,
  cumulative_sells: 1,
  winning_trades: 1,
  losing_trades: 0,
  flat_trades: 0,
  last_transaction: {
    action: 'BUY',
    timestamp: '2026-05-14T00:00:00Z',
    execution_price: 100,
    size_percent: 0.5,
    position_before: 0,
    position_after: 0.5,
    notional_usd: 50,
    balance_before: 10000,
    balance_after: 9950,
    fee: 0.05,
    realized_pnl: 0,
    unrealized_pnl_after: 0,
    ...overrides,
  },
})

describe('LastActionPanel', () => {
  it('renders the panel heading', () => {
    render(<LastActionPanel event={null} />)
    expect(screen.getByRole('heading', { name: /last transaction/i })).toBeInTheDocument()
  })

  it('shows placeholder content when event is null', () => {
    render(<LastActionPanel event={null} />)
    expect(screen.getByTestId('last-transaction-empty')).toBeInTheDocument()
    expect(screen.queryByTestId('last-transaction-direction')).not.toBeInTheDocument()
  })

  it('renders BUY action with distinct visual marker when event is present', () => {
    render(<LastActionPanel event={fakeEvent({ action: 'BUY', execution_price: 105 })} />)
    expect(screen.getByTestId('last-transaction-direction')).toHaveAttribute('data-action', 'BUY')
    expect(screen.getByTestId('last-transaction-price')).toHaveTextContent('$105.00')
  })

  it('renders SELL action with distinct visual marker', () => {
    render(<LastActionPanel event={fakeEvent({ action: 'SELL', execution_price: 99 })} />)
    expect(screen.getByTestId('last-transaction-direction')).toHaveAttribute('data-action', 'SELL')
  })
})
