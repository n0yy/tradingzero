import { describe, expect, it } from 'vitest'
import { fireEvent, render, screen } from '@testing-library/react'

import { PromotionCheckPanel } from './PromotionCheckPanel'
import type { TrainingUpdate } from '@/hooks/useTrainingStream'

function makeEvent(overrides: Partial<TrainingUpdate> = {}): TrainingUpdate {
  return {
    generation: 5,
    training_sharpe: 0.8,
    evaluation_sharpe: 0.9,
    best_evaluation_sharpe: 1.0,
    promoted: false,
    evaluation_executed_trade_count: 6,
    evaluation_sell_realized_exit_count: 3,
    promotion_gate_reasons: [],
    promotion_gate_checks: [],
    balance: 10000,
    pnl: 0,
    trade_win_rate: 0.5,
    progress: 0.5,
    transaction_distribution: { buy: 3, sell: 3, no_transaction: 10 },
    cumulative_buys: 3,
    cumulative_sells: 3,
    winning_trades: 2,
    losing_trades: 1,
    flat_trades: 0,
    last_transaction: null,
    ...overrides,
  }
}

describe('PromotionCheckPanel', () => {
  it('renders "Not promoted" headline when event is null', () => {
    render(<PromotionCheckPanel event={null} />)
    expect(screen.getByText('Not promoted')).toBeInTheDocument()
  })

  it('renders "Not promoted" when promoted is false', () => {
    render(<PromotionCheckPanel event={makeEvent({ promoted: false })} />)
    expect(screen.getByText('Not promoted')).toBeInTheDocument()
  })

  it('renders "Promoted" when promoted is true', () => {
    render(<PromotionCheckPanel event={makeEvent({ promoted: true })} />)
    expect(screen.getByText('Promoted')).toBeInTheDocument()
  })

  it('renders the first promotion_gate_reason as summary text', () => {
    render(
      <PromotionCheckPanel
        event={makeEvent({
          promoted: false,
          promotion_gate_reasons: ['Evaluation Sharpe 0.9000 did not beat target 1.0500.'],
        })}
      />,
    )
    expect(screen.getByTestId('promotion-summary')).toHaveTextContent(
      'Evaluation Sharpe 0.9000 did not beat target 1.0500.',
    )
  })

  it('renders evaluation_sharpe and best_evaluation_sharpe metrics', () => {
    render(
      <PromotionCheckPanel
        event={makeEvent({ evaluation_sharpe: 0.9500, best_evaluation_sharpe: 1.1000 })}
      />,
    )
    expect(screen.getByTestId('promotion-evaluation-sharpe')).toHaveTextContent('0.9500')
    expect(screen.getByTestId('promotion-best-evaluation-sharpe')).toHaveTextContent('1.1000')
  })

  it('renders executed trade count and sell exits', () => {
    render(
      <PromotionCheckPanel
        event={makeEvent({
          evaluation_executed_trade_count: 8,
          evaluation_sell_realized_exit_count: 4,
        })}
      />,
    )
    expect(screen.getByTestId('promotion-executed-trades')).toHaveTextContent('8')
    expect(screen.getByTestId('promotion-sell-exits')).toHaveTextContent('4')
  })

  it('renders each gate check with its message and pass/fail label', () => {
    render(
      <PromotionCheckPanel
        event={makeEvent({
          promotion_gate_checks: [
            {
              name: 'evaluation_sharpe_threshold',
              passed: false,
              actual: 0.9,
              target: 1.05,
              message: 'Evaluation Sharpe threshold',
            },
            {
              name: 'executed_trade_count',
              passed: true,
              actual: 6,
              target: 4,
              message: 'Executed Trade count check',
            },
          ],
        })}
      />,
    )
    expect(screen.getByText('Evaluation Sharpe threshold')).toBeInTheDocument()
    expect(screen.getByText('Executed Trade count check')).toBeInTheDocument()
    const labels = screen.getAllByText(/^(Pass|Fail)$/)
    expect(labels).toHaveLength(2)
    expect(labels[0]).toHaveTextContent('Fail')
    expect(labels[1]).toHaveTextContent('Pass')
  })

  it('renders "No promotion gate checks yet." when checks list is empty', () => {
    render(<PromotionCheckPanel event={makeEvent({ promotion_gate_checks: [] })} />)
    expect(screen.getByText('No promotion gate checks yet.')).toBeInTheDocument()
  })

  it('hides per-anchor detail by default', () => {
    render(<PromotionCheckPanel event={makeEvent()} />)
    expect(screen.queryByTestId('promotion-anchor-label')).not.toBeInTheDocument()
  })

  it('shows per-anchor detail after clicking the collapsible trigger', () => {
    render(<PromotionCheckPanel event={makeEvent({ generation: 7 })} />)
    fireEvent.click(screen.getByRole('button', { name: /per-anchor detail/i }))
    expect(screen.getByTestId('promotion-anchor-label')).toBeInTheDocument()
    expect(screen.getByTestId('promotion-anchor-label')).toHaveTextContent('7')
  })

  it('renders training sharpe as context metric', () => {
    render(<PromotionCheckPanel event={makeEvent({ training_sharpe: 0.8765 })} />)
    expect(screen.getByText(/training sharpe/i)).toBeInTheDocument()
    expect(screen.getByText(/0\.8765/i)).toBeInTheDocument()
  })
})
