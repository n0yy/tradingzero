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

async function jsonOrThrow<T>(res: Response, label: string): Promise<T> {
  if (!res.ok) throw new Error(`${label} failed: ${res.status}`)
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
