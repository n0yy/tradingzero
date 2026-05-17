import { describe, expect, it } from 'vitest'
import { render, screen } from '@testing-library/react'

import { KpiStrip } from './KpiStrip'

describe('KpiStrip', () => {
  it('renders live-only KPI labels', () => {
    render(<KpiStrip event={null} />)
    expect(screen.getByText('Balance')).toBeInTheDocument()
    expect(screen.getByText('PnL')).toBeInTheDocument()
    expect(screen.getByText('Trade Win Rate')).toBeInTheDocument()
    expect(screen.getByText('Progress')).toBeInTheDocument()
  })

  it('renders em-dash placeholders when event is null', () => {
    render(<KpiStrip event={null} />)
    expect(screen.getByTestId('kpi-balance')).toHaveTextContent('—')
    expect(screen.getByTestId('kpi-pnl')).toHaveTextContent('—')
    expect(screen.getByTestId('kpi-trade-win-rate')).toHaveTextContent('—')
    expect(screen.getByTestId('kpi-progress')).toHaveTextContent('—')
  })

  it('renders formatted values when event is present', () => {
    render(
      <KpiStrip
        event={{
          generation: 5,
          training_sharpe: 0.9876,
          evaluation_sharpe: 1.2345,
          best_evaluation_sharpe: 1.5,
          balance: 12500,
          pnl: 250.5,
          trade_win_rate: 0.6,
          progress: 0.4,
          transaction_distribution: { buy: 1, sell: 3, no_transaction: 2 },
          cumulative_buys: 10,
          cumulative_sells: 5,
          winning_trades: 3,
          losing_trades: 2,
          flat_trades: 0,
          last_transaction: {
            action: 'BUY',
            timestamp: '2026-05-14T00:00:00Z',
            execution_price: 100,
            size_percent: 0.5,
            position_before: 0,
            position_after: 0.5,
            notional_usd: 50,
            balance_before: 12500,
            balance_after: 12450,
            fee: 0.05,
            realized_pnl: 0,
            unrealized_pnl_after: 0,
  hold_duration: 0,
          },
        }}
      />,
    )
    expect(screen.getByTestId('kpi-balance')).toHaveTextContent('$12,500.00')
    expect(screen.getByTestId('kpi-pnl')).toHaveTextContent('+$250.50')
    expect(screen.getByTestId('kpi-trade-win-rate')).toHaveTextContent('60.00%')
    expect(screen.getByTestId('kpi-progress')).toHaveTextContent('40.00%')
  })

  it('flags PnL as a loss when negative', () => {
    render(
      <KpiStrip
        event={{
          generation: 1,
          training_sharpe: 0,
          evaluation_sharpe: 0,
          best_evaluation_sharpe: 0,
          balance: 9500,
          pnl: -500,
          trade_win_rate: 0,
          progress: 0,
          transaction_distribution: { buy: 0, sell: 0, no_transaction: 0 },
          cumulative_buys: 0,
          cumulative_sells: 0,
          winning_trades: 0,
          losing_trades: 0,
          flat_trades: 0,
          last_transaction: null,
        }}
      />,
    )
    const pnl = screen.getByTestId('kpi-pnl')
    expect(pnl).toHaveTextContent('-$500.00')
    expect(pnl).toHaveAttribute('data-sign', 'loss')
  })

  it('prefers stepBatch balance/pnl over generation event when present', () => {
    render(
      <KpiStrip
        event={null}
        stepBatch={{
          step: 50,
          generation: 1,
          price: 30100,
          requested_direction: 'BUY',
          requested_size_percent: 0.5,
          transaction_outcome: 'BUY',
          is_transaction: true,
          position_before: 0,
          position_after: 0.4,
          executed_delta: 0.4,
          position: 0.4,
          balance: 10250.75,
          pnl: 250.75,
          rolling_reward: 1.2,
          steps_per_second: 200,
          equity_curve: [10000, 10250.75],
          cost: 0.001,
          cumulative_buys: 1,
          cumulative_sells: 0,
          transaction_distribution: { buy: 1, sell: 0, no_transaction: 0 },
          trade_win_rate: 0,
          winning_trades: 0,
          losing_trades: 0,
          flat_trades: 0,
          executed_trade: {
            action: 'BUY',
            timestamp: '2026-05-14T00:00:00Z',
            execution_price: 30100,
            size_percent: 0.4,
            position_before: 0,
            position_after: 0.4,
            notional_usd: 4000,
            balance_before: 10000,
            balance_after: 10250.75,
            fee: 10,
            realized_pnl: 0,
            unrealized_pnl_after: 0,
  hold_duration: 0,
          },
          timestamp: '2024-01-01T00:00:00Z',
  phase: 'training' as const,
}}
      />,
    )
    expect(screen.getByTestId('kpi-balance')).toHaveTextContent('$10,250.75')
    expect(screen.getByTestId('kpi-pnl')).toHaveTextContent('+$250.75')
  })
})
