import { describe, expect, it } from 'vitest'
import { render, screen } from '@testing-library/react'

import { KpiStrip } from './KpiStrip'

describe('KpiStrip', () => {
  it('renders all 6 KPI labels', () => {
    render(<KpiStrip event={null} />)
    expect(screen.getByText('Sharpe')).toBeInTheDocument()
    expect(screen.getByText('Best Sharpe')).toBeInTheDocument()
    expect(screen.getByText('Balance')).toBeInTheDocument()
    expect(screen.getByText('PnL')).toBeInTheDocument()
    expect(screen.getByText('Win Rate')).toBeInTheDocument()
    expect(screen.getByText('Progress')).toBeInTheDocument()
  })

  it('renders em-dash placeholders when event is null', () => {
    render(<KpiStrip event={null} />)
    const sharpeValue = screen.getByTestId('kpi-sharpe')
    expect(sharpeValue).toHaveTextContent('—')
    expect(screen.getByTestId('kpi-best-sharpe')).toHaveTextContent('—')
    expect(screen.getByTestId('kpi-balance')).toHaveTextContent('—')
    expect(screen.getByTestId('kpi-pnl')).toHaveTextContent('—')
    expect(screen.getByTestId('kpi-win-rate')).toHaveTextContent('—')
    expect(screen.getByTestId('kpi-progress')).toHaveTextContent('—')
  })

  it('renders formatted values when event is present', () => {
    render(
      <KpiStrip
        event={{
          generation: 5,
          current_sharpe: 1.2345,
          best_sharpe: 1.5,
          balance: 12500,
          pnl: 250.5,
          win_rate: 0.6,
          progress: 0.4,
          action_distribution: { buy: 1, hold: 2, sell: 3 },
          cumulative_buys: 10,
          cumulative_sells: 5,
          last_action: {
            action: 'BUY',
            timestamp: '2026-05-14T00:00:00Z',
            execution_price: 100,
            size_percent: 50,
            position_before: 0,
            position_after: 0.5,
            notional_usd: 50,
            balance_before: 12500,
            balance_after: 12450,
            fee: 0.05,
            unrealized_pnl_after: 0,
          },
        }}
      />,
    )
    expect(screen.getByTestId('kpi-sharpe')).toHaveTextContent('1.2345')
    expect(screen.getByTestId('kpi-best-sharpe')).toHaveTextContent('1.5000')
    expect(screen.getByTestId('kpi-balance')).toHaveTextContent('$12,500.00')
    expect(screen.getByTestId('kpi-pnl')).toHaveTextContent('+$250.50')
    expect(screen.getByTestId('kpi-win-rate')).toHaveTextContent('60.00%')
    expect(screen.getByTestId('kpi-progress')).toHaveTextContent('40.00%')
  })

  it('flags PnL as a loss when negative', () => {
    render(
      <KpiStrip
        event={{
          generation: 1,
          current_sharpe: 0,
          best_sharpe: 0,
          balance: 9500,
          pnl: -500,
          win_rate: 0,
          progress: 0,
          action_distribution: { buy: 0, hold: 0, sell: 0 },
          cumulative_buys: 0,
          cumulative_sells: 0,
          last_action: {
            action: 'HOLD',
            timestamp: '2026-05-14T00:00:00Z',
            execution_price: 100,
            size_percent: 0,
            position_before: 0,
            position_after: 0,
            notional_usd: 0,
            balance_before: 10000,
            balance_after: 9500,
            fee: 0,
            unrealized_pnl_after: 0,
          },
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
          last_action: 'BUY',
          position: 0.4,
          balance: 10250.75,
          pnl: 250.75,
          rolling_reward: 1.2,
          steps_per_second: 200,
          equity_curve: [10000, 10250.75],
          timestamp: '2026-05-14T00:00:00Z',
        }}
      />,
    )
    expect(screen.getByTestId('kpi-balance')).toHaveTextContent('$10,250.75')
    expect(screen.getByTestId('kpi-pnl')).toHaveTextContent('+$250.75')
  })
})
