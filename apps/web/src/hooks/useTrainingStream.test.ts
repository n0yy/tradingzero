import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { act, renderHook } from '@testing-library/react'

import { useTrainingStream } from './useTrainingStream'

class MockWebSocket {
  static instances: MockWebSocket[] = []
  static OPEN = 1
  onopen: ((ev: unknown) => void) | null = null
  onclose: ((ev: unknown) => void) | null = null
  onmessage: ((ev: { data: string }) => void) | null = null
  readyState = 0
  url: string

  constructor(url: string) {
    this.url = url
    MockWebSocket.instances.push(this)
    queueMicrotask(() => {
      this.readyState = MockWebSocket.OPEN
      this.onopen?.({})
    })
  }

  close() {
    this.onclose?.({})
  }
}

beforeEach(() => {
  MockWebSocket.instances = []
  vi.useRealTimers()
  ;(globalThis as unknown as { WebSocket: typeof MockWebSocket }).WebSocket = MockWebSocket
})

afterEach(() => {
  vi.useRealTimers()
  vi.restoreAllMocks()
})

function emit(payload: unknown) {
  const ws = MockWebSocket.instances.at(-1)!
  ws.onmessage?.({ data: JSON.stringify(payload) })
}

describe('useTrainingStream step_batch handling', () => {
  it('exposes stepBatch separately from generation event', async () => {
    const { result } = renderHook(() => useTrainingStream())
    await act(async () => {
      await Promise.resolve()
    })

    act(() => {
      emit({
        type: 'step_batch',
        data: {
          step: 10,
          generation: 1,
          price: 30100.5,
          last_action: 'BUY',
          position: 0.3,
          balance: 10010,
          pnl: 10,
          rolling_reward: 0.5,
          steps_per_second: 200,
          equity_curve: [10000, 10010],
          timestamp: '2026-05-14T00:00:00Z',
        },
      })
    })

    expect(result.current.stepBatch).not.toBeNull()
    expect(result.current.stepBatch?.step).toBe(10)
    expect(result.current.stepBatch?.price).toBe(30100.5)
    expect(result.current.event?.last_action.action).toBe('BUY')
    expect(result.current.event?.action_distribution).toEqual({ buy: 1, hold: 0, sell: 0 })
    expect(result.current.event?.balance).toBe(10010)
  })

  it('accumulates a price buffer of recent step_batch prices', async () => {
    const { result } = renderHook(() => useTrainingStream())
    await act(async () => {
      await Promise.resolve()
    })

    act(() => {
      for (let i = 1; i <= 3; i += 1) {
        emit({
          type: 'step_batch',
          data: {
            step: i,
            generation: 1,
            price: 30000 + i,
            last_action: 'HOLD',
            position: 0,
            balance: 10000,
            pnl: 0,
            rolling_reward: 0,
            steps_per_second: 100,
            equity_curve: [10000],
            timestamp: '2026-05-14T00:00:00Z',
          },
        })
      }
    })

    expect(result.current.priceBuffer.map((p) => p.value)).toEqual([30001, 30002, 30003])
    expect(result.current.priceBuffer[0]?.time).toBe(1)
    expect(result.current.event?.action_distribution).toEqual({ buy: 0, hold: 3, sell: 0 })
  })

  it('caps the price buffer at 500 points', async () => {
    const { result } = renderHook(() => useTrainingStream())
    await act(async () => {
      await Promise.resolve()
    })

    act(() => {
      for (let i = 1; i <= 600; i += 1) {
        emit({
          type: 'step_batch',
          data: {
            step: i,
            generation: 1,
            price: 30000 + i,
            last_action: 'HOLD',
            position: 0,
            balance: 10000,
            pnl: 0,
            rolling_reward: 0,
            steps_per_second: 100,
            equity_curve: [10000],
            timestamp: '2026-05-14T00:00:00Z',
          },
        })
      }
    })

    expect(result.current.priceBuffer).toHaveLength(500)
    expect(result.current.priceBuffer[0]?.time).toBe(101)
    expect(result.current.priceBuffer.at(-1)?.time).toBe(600)
  })

  it('still records training_update into event field', async () => {
    const { result } = renderHook(() => useTrainingStream())
    await act(async () => {
      await Promise.resolve()
    })

    act(() => {
      emit({
        type: 'training_update',
        data: {
          generation: 1,
          current_sharpe: 1.0,
          best_sharpe: 1.0,
          balance: 10000,
          pnl: 0,
          win_rate: 0.5,
          progress: 0.1,
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
      })
    })

    expect(result.current.event?.generation).toBe(1)
  })

  it('reconnects after the websocket closes unexpectedly', async () => {
    vi.useFakeTimers()
    const { result } = renderHook(() => useTrainingStream())
    await act(async () => {
      await Promise.resolve()
    })

    const firstSocket = MockWebSocket.instances.at(-1)!

    act(() => {
      firstSocket.close()
    })

    expect(result.current.connected).toBe(false)

    await act(async () => {
      await vi.advanceTimersByTimeAsync(500)
      await Promise.resolve()
    })

    expect(MockWebSocket.instances).toHaveLength(2)
    expect(result.current.connected).toBe(true)
  })
})
