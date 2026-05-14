import { beforeEach, describe, expect, it, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router'

import App from './App'
import { formatUsd } from './lib/format'

const streamMock = vi.hoisted(() => ({
  current: { event: null as unknown, stepBatch: null as unknown, priceBuffer: [] as unknown, connected: true },
}))

vi.mock('./hooks/useTrainingStream', () => ({
  useTrainingStream: () => streamMock.current,
}))

function setStream(next: { event: unknown; connected: boolean; stepBatch?: unknown; priceBuffer?: unknown }) {
  streamMock.current = {
    event: next.event,
    stepBatch: next.stepBatch ?? null,
    priceBuffer: next.priceBuffer ?? [],
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

globalThis.fetch = vi.fn(async (input: RequestInfo | URL) => {
  const url = String(input)
  if (url.endsWith('/runs/status')) {
    return new Response(JSON.stringify(runStatusMock.current), { status: 200 })
  }
  if (url.endsWith('/runs')) {
    return new Response(JSON.stringify({ runs: [] }), { status: 200 })
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
  return new Response('{}', { status: 200 })
}) as typeof fetch

vi.mock('./components/PriceChart', () => ({
  default: () => <div>Price Chart Mock</div>,
}))

vi.mock('./components/AnalyticsChart', () => ({
  default: () => <div>Analytics Chart Mock</div>,
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
    setStream({ event: null, connected: true })
    setRunStatus({ state: 'idle', run_id: null, started_at: null, finished_at: null, error: null })
  })

  it('formats usd with 2 decimals and separators', () => {
    expect(formatUsd(123000)).toBe('$123,000.00')
  })

  it('renders key metrics header', () => {
    renderApp()
    expect(screen.getByText('TradingZero Dashboard')).toBeInTheDocument()
    expect(screen.getByText('Sharpe')).toBeInTheDocument()
    expect(screen.getByText('Best Sharpe')).toBeInTheDocument()
    expect(screen.getByText('Balance')).toBeInTheDocument()
    expect(screen.getByText('PnL')).toBeInTheDocument()
    expect(screen.getByTestId('start-run')).toBeInTheDocument()
  })

  it('renders side nav with Live View, Config, Runs, Errors at /', () => {
    renderApp('/')
    const nav = screen.getByRole('navigation', { name: /primary/i })
    expect(nav).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /live view/i })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /^config$/i })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /^runs$/i })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /^errors$/i })).toBeInTheDocument()
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

  it('renders Error Explorer on /errors', async () => {
    renderApp('/errors')
    expect(await screen.findByRole('heading', { name: /error explorer/i })).toBeInTheDocument()
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
        current_sharpe: 0.1,
        best_sharpe: 0.2,
        balance: 10000,
        pnl: 50,
        win_rate: 0.6,
        progress: 0.3,
        action_distribution: { buy: 1, hold: 2, sell: 0 },
        cumulative_buys: 1,
        cumulative_sells: 0,
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
