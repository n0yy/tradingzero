import { describe, expect, it } from 'vitest'
import { render, screen } from '@testing-library/react'

import { ActionDistributionPanel } from './ActionDistributionPanel'
import type { TrainingUpdate } from '@/hooks/useTrainingStream'

const fakeEvent = (overrides: Partial<TrainingUpdate> = {}): TrainingUpdate => ({
  generation: 5,
  training_sharpe: 0,
  evaluation_sharpe: 0,
  best_evaluation_sharpe: 0,
  balance: 10000,
  pnl: 0,
  trade_win_rate: 0.5,
  progress: 0.1,
  transaction_distribution: { buy: 4, sell: 2, no_transaction: 6 },
  cumulative_buys: 40,
  cumulative_sells: 25,
  winning_trades: 1,
  losing_trades: 1,
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
  hold_duration: 0,
  },
  ...overrides,
})

describe('ActionDistributionPanel', () => {
  it('renders the panel heading', () => {
    render(<ActionDistributionPanel event={null} />)
    expect(screen.getByRole('heading', { name: /transaction distribution/i })).toBeInTheDocument()
  })

  it('shows placeholder when event is null', () => {
    render(<ActionDistributionPanel event={null} />)
    expect(screen.getByTestId('distribution-empty')).toBeInTheDocument()
    expect(screen.queryByTestId('distribution-buy')).not.toBeInTheDocument()
  })

  it('renders BUY/NO TRANSACTION/SELL counts when event is present', () => {
    render(<ActionDistributionPanel event={fakeEvent()} />)
    expect(screen.getByTestId('distribution-buy')).toHaveTextContent('4')
    expect(screen.getByTestId('distribution-no-transaction')).toHaveTextContent('6')
    expect(screen.getByTestId('distribution-sell')).toHaveTextContent('2')
  })

  it('renders cumulative buys and sells when event is present', () => {
    render(<ActionDistributionPanel event={fakeEvent()} />)
    expect(screen.getByTestId('cumulative-buys')).toHaveTextContent('40')
    expect(screen.getByTestId('cumulative-sells')).toHaveTextContent('25')
  })

  it('does not render cumulative numbers when event is null', () => {
    render(<ActionDistributionPanel event={null} />)
    expect(screen.queryByTestId('cumulative-buys')).not.toBeInTheDocument()
    expect(screen.queryByTestId('cumulative-sells')).not.toBeInTheDocument()
  })
})
