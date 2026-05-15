export type RunStatus = {
  state: string
  run_id: string | null
  started_at: string | null
  finished_at: string | null
  error: string | null
}

export type RunHistoryItem = {
  run_id: string
  state: string
  started_at: string | null
  finished_at: string | null
  error: string | null
  evaluation_summary?: {
    latest_promotion_outcome: 'promoted' | 'not_promoted'
    best_evaluation_sharpe: number
  } | null
}

export type RunErrorItem = {
  code: string
  message: string
  details: string | null
  created_at: string
}

export type SafeConfigPayload = {
  data: { exchange: string; symbol: string; timeframe: string; window_size: number }
  env: { initial_balance: number; transaction_cost: number; episode_length: number }
  agent: {
    learning_rate: number
    n_steps: number
    batch_size: number
    clip_range: number
    total_episodes: number
    promote_threshold: number
  }
  self_play: { checkpoint_interval: number; checkpoint_dir: string }
}

export type ActiveConfigResponse = {
  version: string | null
  created_at: string | null
  config: SafeConfigPayload | null
}

export type BattleTrade = {
  action: 'BUY' | 'SELL'
  timestamp: string
  execution_price: number
  size_percent: number
  position_before: number
  position_after: number
  notional_usd: number
  balance_before: number
  balance_after: number
  fee: number
  realized_pnl: number
  unrealized_pnl_after: number
}

export type BattleResult = {
  checkpoint: string
  symbol: string
  timeframe: string
  initial_balance: number
  final_balance: number
  pnl: number
  pnl_pct: number
  total_steps: number
  total_trades: number
  trade_win_rate: number
  winning_trades: number
  losing_trades: number
  flat_trades: number
  transaction_distribution: { buy: number; sell: number; no_transaction: number }
  price_series: number[]
  equity_curve: number[]
  executed_trades: BattleTrade[]
}

async function jsonOrThrow<T>(res: Response, label: string): Promise<T> {
  if (!res.ok) {
    let detail = ''
    try {
      const payload = (await res.json()) as {
        detail?: { error?: { message?: string } }
        error?: { message?: string }
        message?: string
      }
      detail =
        payload?.detail?.error?.message ??
        payload?.error?.message ??
        payload?.message ??
        ''
    } catch {
      detail = ''
    }
    throw new Error(detail ? `${label} failed: ${detail}` : `${label} failed: ${res.status}`)
  }
  return (await res.json()) as T
}

export async function fetchRunStatus(): Promise<RunStatus> {
  const res = await fetch('/runs/status')
  return jsonOrThrow<RunStatus>(res, 'fetch run status')
}

export async function startRun(): Promise<RunStatus> {
  const res = await fetch('/runs/start', { method: 'POST' })
  return jsonOrThrow<RunStatus>(res, 'start run')
}

export async function stopRun(): Promise<RunStatus> {
  const res = await fetch('/runs/stop', { method: 'POST' })
  return jsonOrThrow<RunStatus>(res, 'stop run')
}

export async function retryRun(): Promise<RunStatus> {
  const res = await fetch('/runs/retry', { method: 'POST' })
  return jsonOrThrow<RunStatus>(res, 'retry run')
}

export async function fetchRuns(): Promise<{ runs: RunHistoryItem[] }> {
  const res = await fetch('/runs')
  return jsonOrThrow<{ runs: RunHistoryItem[] }>(res, 'fetch runs')
}

export async function fetchRunErrors(runId: string): Promise<{ errors: RunErrorItem[] }> {
  const res = await fetch(`/runs/${runId}/errors`)
  return jsonOrThrow<{ errors: RunErrorItem[] }>(res, 'fetch run errors')
}

export async function fetchActiveConfig(): Promise<ActiveConfigResponse> {
  const res = await fetch('/config/active')
  return jsonOrThrow<ActiveConfigResponse>(res, 'fetch active config')
}

export async function saveActiveConfig(config: SafeConfigPayload): Promise<ActiveConfigResponse> {
  const res = await fetch('/config/active', {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(config),
  })
  return jsonOrThrow<ActiveConfigResponse>(res, 'save active config')
}

export async function runBestBattle(): Promise<BattleResult> {
  const res = await fetch('/battle/best', { method: 'POST' })
  return jsonOrThrow<BattleResult>(res, 'run best battle')
}
