import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { fetchRunStatus, startRun, stopRun, retryRun, fetchRuns, fetchRunErrors, fetchActiveConfig, saveActiveConfig } from './api'

const okJson = (body: unknown, status = 200) =>
  new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } })

const fetchMock = vi.fn<typeof fetch>()

beforeEach(() => {
  fetchMock.mockReset()
  globalThis.fetch = fetchMock as unknown as typeof fetch
})

afterEach(() => {
  vi.restoreAllMocks()
})

describe('api client', () => {
  it('fetchRunStatus calls GET /runs/status', async () => {
    fetchMock.mockResolvedValueOnce(okJson({ state: 'idle', run_id: null, started_at: null, finished_at: null, error: null }))
    const out = await fetchRunStatus()
    expect(fetchMock).toHaveBeenCalledWith('/runs/status')
    expect(out.state).toBe('idle')
  })

  it('startRun POSTs /runs/start', async () => {
    fetchMock.mockResolvedValueOnce(okJson({ state: 'running', run_id: 'r1', started_at: null, finished_at: null, error: null }, 202))
    const out = await startRun()
    expect(fetchMock).toHaveBeenCalledWith('/runs/start', { method: 'POST' })
    expect(out.run_id).toBe('r1')
  })

  it('stopRun POSTs /runs/stop', async () => {
    fetchMock.mockResolvedValueOnce(okJson({ state: 'stopping', run_id: 'r1', started_at: null, finished_at: null, error: null }, 202))
    await stopRun()
    expect(fetchMock).toHaveBeenCalledWith('/runs/stop', { method: 'POST' })
  })

  it('retryRun POSTs /runs/retry', async () => {
    fetchMock.mockResolvedValueOnce(okJson({ state: 'running', run_id: 'r2', started_at: null, finished_at: null, error: null }, 202))
    await retryRun()
    expect(fetchMock).toHaveBeenCalledWith('/runs/retry', { method: 'POST' })
  })

  it('fetchRuns calls GET /runs', async () => {
    fetchMock.mockResolvedValueOnce(okJson({ runs: [] }))
    const out = await fetchRuns()
    expect(fetchMock).toHaveBeenCalledWith('/runs')
    expect(out.runs).toEqual([])
  })

  it('fetchRunErrors calls GET /runs/<id>/errors', async () => {
    fetchMock.mockResolvedValueOnce(okJson({ errors: [] }))
    await fetchRunErrors('abc')
    expect(fetchMock).toHaveBeenCalledWith('/runs/abc/errors')
  })

  it('fetchActiveConfig calls GET /config/active', async () => {
    fetchMock.mockResolvedValueOnce(okJson({ version: 'v1', created_at: null, config: null }))
    await fetchActiveConfig()
    expect(fetchMock).toHaveBeenCalledWith('/config/active')
  })

  it('saveActiveConfig PUTs /config/active with JSON body', async () => {
    fetchMock.mockResolvedValueOnce(okJson({ version: 'v2', created_at: null, config: null }))
    const payload = {
      data: { exchange: 'binance', symbol: 'BTC/USDT', timeframe: '15m', window_size: 60 },
      env: { initial_balance: 10000, transaction_cost: 0.001, episode_length: 500 },
      agent: { learning_rate: 0.0001, n_steps: 4096, batch_size: 128, clip_range: 0.2, total_episodes: 1000, promote_threshold: 0.05 },
      self_play: { checkpoint_interval: 10, checkpoint_dir: 'agent/checkpoints/' },
    }
    await saveActiveConfig(payload)
    expect(fetchMock).toHaveBeenCalledWith('/config/active', {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    })
  })

  it('throws when response is not ok', async () => {
    fetchMock.mockResolvedValueOnce(new Response('boom', { status: 500 }))
    await expect(fetchRunStatus()).rejects.toThrow()
  })
})
