import { beforeEach, describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router'

import App from './App'
import { formatUsd } from './lib/format'

const streamMock = vi.hoisted(() => ({
  current: {
    event: null as unknown,
    stepBatch: null as unknown,
    priceBuffer: [] as unknown,
    profitLossDistribution: { profit: 0, loss: 0, flat: 0 } as unknown,
    connected: true,
  },
}))

vi.mock('./hooks/useTrainingStream', () => ({
  useTrainingStream: () => streamMock.current,
}))

function setStream(next: {
  event: unknown
  connected: boolean
  stepBatch?: unknown
  priceBuffer?: unknown
  profitLossDistribution?: unknown
}) {
  streamMock.current = {
    event: next.event,
    stepBatch: next.stepBatch ?? null,
    priceBuffer: next.priceBuffer ?? [],
    profitLossDistribution: next.profitLossDistribution ?? { profit: 0, loss: 0, flat: 0 },
    connected: next.connected,
  }
}

const runStatusMock = vi.hoisted(() => ({
  current: { state: 'idle', run_id: null, started_at: null, finished_at: null, error: null } as {
    state: string
    run_id: string | null
    started_at: string | null
    finished_at: string | null
    error: string | null
  },
}))

function setRunStatus(next: Partial<typeof runStatusMock.current>) {
  runStatusMock.current = { ...runStatusMock.current, ...next }
}

const runsHistoryMock = vi.hoisted(() => ({
  current: { runs: [] as Array<Record<string, unknown>> },
}))

function setRunsHistory(runs: Array<Record<string, unknown>>) {
  runsHistoryMock.current = { runs }
}

globalThis.fetch = vi.fn(async (input: RequestInfo | URL) => {
  const url = String(input)
  if (url.endsWith('/runs/status')) {
    return new Response(JSON.stringify(runStatusMock.current), { status: 200 })
  }
  if (url.endsWith('/runs')) {
    return new Response(JSON.stringify(runsHistoryMock.current), { status: 200 })
  }
  if (url.includes('/runs/') && url.endsWith('/errors')) {
    return new Response(JSON.stringify({ errors: [] }), { status: 200 })
  }
  if (url.endsWith('/runs/retry')) {
    return new Response(JSON.stringify({ state: 'running', run_id: 'x', started_at: null, finished_at: null, error: null }), { status: 202 })
  }
  if (url.endsWith('/runs/start')) {
    return new Response(JSON.stringify({ state: 'running', run_id: 'x', started_at: null, finished_at: null, error: null }), { status: 202 })
  }
  if (url.endsWith('/runs/stop')) {
    return new Response(JSON.stringify({ state: 'stopping', run_id: 'x', started_at: null, finished_at: null, error: null }), { status: 202 })
  }
  if (url.endsWith('/config/active')) {
    return new Response(
      JSON.stringify({
        version: 'v1',
        created_at: '2026-05-14T00:00:00Z',
        config: {
          data: { exchange: 'binance', symbol: 'BTC/USDT', timeframe: '15m', window_size: 60 },
          env: { initial_balance: 10000, transaction_cost: 0.001, episode_length: 500 },
          agent: { learning_rate: 0.0001, n_steps: 4096, batch_size: 128, clip_range: 0.2, total_episodes: 1000, promote_threshold: 0.05 },
          self_play: { checkpoint_interval: 10, checkpoint_dir: 'agent/checkpoints/' },
        },
      }),
      { status: 200 },
    )
  }
  if (url.endsWith('/battle/best')) {
    return new Response(
      JSON.stringify({
        checkpoint: 'agent/checkpoints/best.zip',
        symbol: 'BTC/USDT',
        timeframe: '15m',
        initial_balance: 10000,
        final_balance: 10120,
        pnl: 120,
        pnl_pct: 0.012,
        total_steps: 500,
        total_trades: 8,
        trade_win_rate: 0.75,
        winning_trades: 3,
        losing_trades: 1,
        flat_trades: 0,
        transaction_distribution: { buy: 5, sell: 4, no_transaction: 491 },
        price_series: [100, 101],
        equity_curve: [10000, 10120],
        executed_trades: [],
      }),
      { status: 200 },
    )
  }
  return new Response('{}', { status: 200 })
}) as typeof fetch

vi.mock('./components/PriceChart', () => ({
  default: () => <div>Price Chart Mock</div>,
}))

function renderApp(initialPath: string = '/') {
  const qc = new QueryClient()
  render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={[initialPath]}>
        <App />
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

describe('dashboard', () => {
  beforeEach(() => {
    setStream({ event: null, connected: true, profitLossDistribution: { profit: 0, loss: 0, flat: 0 } })
    setRunStatus({ state: 'idle', run_id: null, started_at: null, finished_at: null, error: null })
    setRunsHistory([])
  })

  it('formats usd with 2 decimals and separators', () => {
    expect(formatUsd(123000)).toBe('$123,000.00')
  })

  it('renders key metrics header', () => {
    renderApp()
    expect(screen.getByText('TradingZero Dashboard')).toBeInTheDocument()
    expect(screen.getByText('Balance')).toBeInTheDocument()
    expect(screen.getByText('PnL')).toBeInTheDocument()
    expect(screen.getByText('Trade Win Rate')).toBeInTheDocument()
    expect(screen.getByText('Progress')).toBeInTheDocument()
    expect(screen.getByText('Promotion Check')).toBeInTheDocument()
    expect(screen.getByTestId('start-run')).toBeInTheDocument()
  })

  it('renders promotion decision summary and reason with checklist values', () => {
    setStream({
      event: {
        generation: 9,
        training_sharpe: 0.77,
        evaluation_sharpe: 0.95,
        best_evaluation_sharpe: 1.1,
        promoted: false,
        evaluation_executed_trade_count: 8,
        evaluation_sell_realized_exit_count: 3,
        promotion_gate_reasons: ['Evaluation Sharpe 0.9500 did not beat target 1.0500.'],
        promotion_gate_checks: [
          {
            name: 'evaluation_sharpe_threshold',
            passed: false,
            actual: 0.95,
            target: 1.05,
            message: 'Evaluation Sharpe threshold',
          },
        ],
        balance: 10000,
        pnl: 10,
        trade_win_rate: 0.6,
        progress: 0.4,
        transaction_distribution: { buy: 1, sell: 1, no_transaction: 1 },
        cumulative_buys: 1,
        cumulative_sells: 1,
        winning_trades: 1,
        losing_trades: 1,
        flat_trades: 0,
        last_transaction: null,
      },
      connected: true,
    })
    renderApp('/')
    expect(screen.getByText('Not promoted')).toBeInTheDocument()
    expect(screen.getByTestId('promotion-summary')).toHaveTextContent('did not beat target')
    expect(screen.getByText('Evaluation Sharpe threshold')).toBeInTheDocument()
    expect(screen.getByTestId('promotion-evaluation-sharpe')).toHaveTextContent('0.9500')
    expect(screen.getByTestId('promotion-best-evaluation-sharpe')).toHaveTextContent('1.1000')
    expect(screen.getByTestId('promotion-executed-trades')).toHaveTextContent('8')
    expect(screen.getByTestId('promotion-sell-exits')).toHaveTextContent('3')
  })

  it('keeps per-anchor detail collapsed by default and expands on demand', () => {
    renderApp('/')
    expect(screen.queryByTestId('promotion-anchor-label')).not.toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: /per-anchor detail/i }))
    expect(screen.getByTestId('promotion-anchor-label')).toBeInTheDocument()
  })

  it('renders side nav with Live View, Battle, Config, Runs, Errors at /', () => {
    renderApp('/')
    const nav = screen.getByRole('navigation', { name: /primary/i })
    expect(nav).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /live view/i })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /battle/i })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /^config$/i })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /^runs$/i })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /^errors$/i })).toBeInTheDocument()
  })

  it('renders sidebar footer utility rows for time mode and theme placeholder', () => {
    renderApp('/')
    expect(screen.getByRole('button', { name: /^time$/i })).toBeInTheDocument()
    expect(screen.getByText('UTC')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /^theme$/i })).toBeDisabled()
    expect(screen.getByText('Dark/Light')).toBeInTheDocument()
  })

  it('renders sidebar trigger for collapsible shell control', () => {
    renderApp('/')
    expect(screen.getByTestId('sidebar-trigger')).toBeInTheDocument()
  })

  it('marks Live View as the active nav target at /', () => {
    renderApp('/')
    const liveLink = screen.getByRole('link', { name: /live view/i })
    const configLink = screen.getByRole('link', { name: /^config$/i })
    expect(liveLink).toHaveAttribute('aria-current', 'page')
    expect(configLink).not.toHaveAttribute('aria-current', 'page')
  })

  it('renders Config form on /config', async () => {
    renderApp('/config')
    expect(await screen.findByRole('button', { name: /save revision/i })).toBeInTheDocument()
    expect(screen.getByText(/exchange/i)).toBeInTheDocument()
    expect(screen.getByText(/symbol/i)).toBeInTheDocument()
  })

  it('groups Config fields into Data, Environment, Agent, and Self-play sections', async () => {
    renderApp('/config')
    expect(await screen.findByRole('group', { name: /^data$/i })).toBeInTheDocument()
    expect(screen.getByRole('group', { name: /environment/i })).toBeInTheDocument()
    expect(screen.getByRole('group', { name: /^agent$/i })).toBeInTheDocument()
    expect(screen.getByRole('group', { name: /self-play/i })).toBeInTheDocument()
  })

  it('marks Config as the active nav target at /config', () => {
    renderApp('/config')
    const configLink = screen.getByRole('link', { name: /^config$/i })
    const liveLink = screen.getByRole('link', { name: /live view/i })
    expect(configLink).toHaveAttribute('aria-current', 'page')
    expect(liveLink).not.toHaveAttribute('aria-current', 'page')
  })

  it('does not render Config form on Live View', () => {
    renderApp('/')
    expect(screen.queryByRole('button', { name: /save revision/i })).not.toBeInTheDocument()
  })

  it('does not render Live View KPI strip on Config', () => {
    renderApp('/config')
    expect(screen.queryByText('Sharpe')).not.toBeInTheDocument()
    expect(screen.queryByText('Best Sharpe')).not.toBeInTheDocument()
    expect(screen.queryByTestId('start-run')).not.toBeInTheDocument()
  })

  it('renders Run History on /runs', async () => {
    renderApp('/runs')
    expect(await screen.findByRole('heading', { name: /run history/i })).toBeInTheDocument()
  })

  it('renders compact evaluation summary labels in runs history when available', async () => {
    setRunsHistory([
      {
        run_id: 'run-123',
        state: 'done',
        started_at: '2026-05-15T10:00:00Z',
        finished_at: '2026-05-15T10:10:00Z',
        error: null,
        evaluation_summary: {
          latest_promotion_outcome: 'promoted',
          best_evaluation_sharpe: 1.23,
        },
      },
    ])
    renderApp('/runs')
    expect(await screen.findByText(/promotion:/i)).toBeInTheDocument()
    expect(screen.getByText(/best eval sharpe:/i)).toBeInTheDocument()
    expect(screen.getByText(/promoted/i)).toBeInTheDocument()
    expect(screen.getByText(/1\.2300/i)).toBeInTheDocument()
  })

  it('renders Error Explorer on /errors', async () => {
    renderApp('/errors')
    expect(await screen.findByRole('heading', { name: /error explorer/i })).toBeInTheDocument()
  })

  it('renders Battle page on /battle', async () => {
    renderApp('/battle')
    expect(await screen.findByRole('button', { name: /run best agent/i })).toBeInTheDocument()
    expect(screen.getByTestId('battle-checkpoint')).toHaveTextContent('best.zip')
  })

  it('does not render Run History on Live View', () => {
    renderApp('/')
    expect(screen.queryByRole('heading', { name: /run history/i })).not.toBeInTheDocument()
    expect(screen.queryByRole('heading', { name: /error explorer/i })).not.toBeInTheDocument()
  })

  it('renders an Idle state badge when run is idle and stream connected', () => {
    renderApp('/')
    const badge = screen.getByTestId('live-view-state')
    expect(badge).toHaveTextContent(/idle/i)
    expect(screen.getByTestId('chart-state-helper')).toHaveTextContent(/idle/i)
  })

  it('renders a Disconnected state when stream is disconnected, even if backend says running', () => {
    setStream({ event: null, connected: false })
    setRunStatus({ state: 'running', run_id: 'r1' })
    renderApp('/')
    expect(screen.getByTestId('live-view-state')).toHaveTextContent(/disconnected/i)
    expect(screen.getByTestId('chart-state-helper')).toHaveTextContent(/disconnected/i)
  })

  it('renders a Waiting state when run is running but no event has arrived yet', async () => {
    setStream({ event: null, connected: true })
    setRunStatus({ state: 'running', run_id: 'r1' })
    renderApp('/')
    await waitFor(() => {
      expect(screen.getByTestId('live-view-state')).toHaveTextContent(/waiting/i)
    })
    expect(screen.getByTestId('chart-state-helper')).toHaveTextContent(/waiting/i)
  })

  it('hides the chart state helper when running and an event has arrived', async () => {
    setStream({
      event: {
        generation: 1,
        training_sharpe: 0.1,
        evaluation_sharpe: 0.1,
        best_evaluation_sharpe: 0.2,
        balance: 10000,
        pnl: 50,
        trade_win_rate: 0.6,
        progress: 0.3,
        transaction_distribution: { buy: 1, sell: 0, no_transaction: 2 },
        cumulative_buys: 1,
        cumulative_sells: 0,
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
        },
      },
      connected: true,
    })
    setRunStatus({ state: 'running', run_id: 'r1' })
    renderApp('/')
    await waitFor(() => {
      expect(screen.getByTestId('live-view-state')).toHaveTextContent(/running/i)
    })
    expect(screen.queryByTestId('chart-state-helper')).not.toBeInTheDocument()
  })

  it('shows only Start at idle (no Stop, no Retry)', () => {
    renderApp('/')
    expect(screen.getByTestId('start-run')).toBeInTheDocument()
    expect(screen.queryByTestId('stop-run')).not.toBeInTheDocument()
    expect(screen.queryByTestId('retry-run')).not.toBeInTheDocument()
  })

  it('shows only Stop while running', async () => {
    setRunStatus({ state: 'running', run_id: 'r1' })
    renderApp('/')
    await waitFor(() => {
      expect(screen.getByTestId('live-view-state')).toHaveTextContent(/waiting|running/i)
    })
    expect(screen.queryByTestId('start-run')).not.toBeInTheDocument()
    expect(screen.getByTestId('stop-run')).toBeInTheDocument()
    expect(screen.queryByTestId('retry-run')).not.toBeInTheDocument()
  })

  it('shows Start and Retry when run errored', async () => {
    setRunStatus({ state: 'error', run_id: 'r1', error: 'OOM' })
    renderApp('/')
    await waitFor(() => {
      expect(screen.getByTestId('live-view-state')).toHaveTextContent(/error/i)
    })
    expect(screen.getByTestId('start-run')).toBeInTheDocument()
    expect(screen.queryByTestId('stop-run')).not.toBeInTheDocument()
    expect(screen.getByTestId('retry-run')).toBeInTheDocument()
  })

  it('shows Start and Retry when run is done', async () => {
    setRunStatus({ state: 'done', run_id: 'r1' })
    renderApp('/')
    await waitFor(() => {
      expect(screen.getByTestId('live-view-state')).toHaveTextContent(/done/i)
    })
    expect(screen.getByTestId('start-run')).toBeInTheDocument()
    expect(screen.queryByTestId('stop-run')).not.toBeInTheDocument()
    expect(screen.getByTestId('retry-run')).toBeInTheDocument()
  })

  it('keeps Start reachable while disconnected', () => {
    setStream({ event: null, connected: false })
    setRunStatus({ state: 'idle', run_id: null })
    renderApp('/')
    expect(screen.getByTestId('live-view-state')).toHaveTextContent(/disconnected/i)
    expect(screen.getByTestId('start-run')).toBeInTheDocument()
    expect(screen.queryByTestId('stop-run')).not.toBeInTheDocument()
  })
})
