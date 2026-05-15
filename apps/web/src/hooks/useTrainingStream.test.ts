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
          requested_direction: 'BUY',
          requested_size_percent: 0.3,
          transaction_outcome: 'BUY',
          is_transaction: true,
          position_before: 0,
          position_after: 0.3,
          executed_delta: 0.3,
          position: 0.3,
          balance: 10010,
          pnl: 10,
          rolling_reward: 0.5,
          steps_per_second: 200,
          equity_curve: [10000, 10010],
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
            execution_price: 30100.5,
            size_percent: 0.3,
            position_before: 0,
            position_after: 0.3,
            notional_usd: 3000,
            balance_before: 10000,
            balance_after: 10010,
            fee: 10,
            realized_pnl: 0,
            unrealized_pnl_after: 0,
          },
          timestamp: '2026-05-14T00:00:00Z',
        },
      })
    })

    expect(result.current.stepBatch).not.toBeNull()
    expect(result.current.stepBatch?.step).toBe(10)
    expect(result.current.stepBatch?.price).toBe(30100.5)
    expect(result.current.event?.last_transaction?.action).toBe('BUY')
    expect(result.current.event?.transaction_distribution).toEqual({ buy: 1, sell: 0, no_transaction: 0 })
    expect(result.current.event?.balance).toBe(10010)
    expect(result.current.profitLossDistribution).toEqual({ profit: 1, loss: 0, flat: 0 })
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
            requested_direction: 'HOLD',
            requested_size_percent: 0,
            transaction_outcome: 'NO_TRANSACTION',
            is_transaction: false,
            position_before: 0,
            position_after: 0,
            executed_delta: 0,
            position: 0,
            balance: 10000,
            pnl: 0,
            rolling_reward: 0,
            steps_per_second: 100,
            equity_curve: [10000],
            cost: 0,
            cumulative_buys: 0,
            cumulative_sells: 0,
            transaction_distribution: { buy: 0, sell: 0, no_transaction: i },
            trade_win_rate: 0,
            winning_trades: 0,
            losing_trades: 0,
            flat_trades: 0,
            executed_trade: null,
            timestamp: '2026-05-14T00:00:00Z',
          },
        })
      }
    })

    expect(result.current.priceBuffer.map((p) => p.value)).toEqual([30001, 30002, 30003])
    expect(result.current.priceBuffer[0]?.time).toBe(1)
    expect(result.current.event?.transaction_distribution).toEqual({ buy: 0, sell: 0, no_transaction: 3 })
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
            requested_direction: 'HOLD',
            requested_size_percent: 0,
            transaction_outcome: 'NO_TRANSACTION',
            is_transaction: false,
            position_before: 0,
            position_after: 0,
            executed_delta: 0,
            position: 0,
            balance: 10000,
            pnl: 0,
            rolling_reward: 0,
            steps_per_second: 100,
            equity_curve: [10000],
            cost: 0,
            cumulative_buys: 0,
            cumulative_sells: 0,
            transaction_distribution: { buy: 0, sell: 0, no_transaction: i },
            trade_win_rate: 0,
            winning_trades: 0,
            losing_trades: 0,
            flat_trades: 0,
            executed_trade: null,
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
          trade_win_rate: 0.5,
          progress: 0.1,
          transaction_distribution: { buy: 1, sell: 0, no_transaction: 2 },
          cumulative_buys: 1,
          cumulative_sells: 0,
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
          },
        },
      })
    })

    expect(result.current.event?.generation).toBe(1)
  })

  it('tracks profit, loss, and flat step outcomes from equity changes', async () => {
    const { result } = renderHook(() => useTrainingStream())
    await act(async () => {
      await Promise.resolve()
    })

    act(() => {
      emit({
        type: 'step_batch',
        data: {
          step: 1,
          generation: 1,
          price: 30001,
          requested_direction: 'BUY',
          requested_size_percent: 0.25,
          transaction_outcome: 'BUY',
          is_transaction: true,
          position_before: 0,
          position_after: 0.25,
          executed_delta: 0.25,
          position: 0.25,
          balance: 10010,
          pnl: 10,
          rolling_reward: 0.2,
          steps_per_second: 100,
          equity_curve: [10000, 10010],
          cost: 0.001,
          cumulative_buys: 1,
          cumulative_sells: 0,
          transaction_distribution: { buy: 1, sell: 0, no_transaction: 0 },
          trade_win_rate: 0,
          winning_trades: 0,
          losing_trades: 0,
          flat_trades: 0,
          executed_trade: null,
          timestamp: '2026-05-14T00:00:00Z',
        },
      })
      emit({
        type: 'step_batch',
        data: {
          step: 2,
          generation: 1,
          price: 30002,
          requested_direction: 'HOLD',
          requested_size_percent: 0,
          transaction_outcome: 'NO_TRANSACTION',
          is_transaction: false,
          position_before: 0.25,
          position_after: 0.25,
          executed_delta: 0,
          position: 0.25,
          balance: 10005,
          pnl: 5,
          rolling_reward: -0.1,
          steps_per_second: 100,
          equity_curve: [10010, 10005],
          cost: 0,
          cumulative_buys: 1,
          cumulative_sells: 0,
          transaction_distribution: { buy: 1, sell: 0, no_transaction: 1 },
          trade_win_rate: 0,
          winning_trades: 0,
          losing_trades: 0,
          flat_trades: 0,
          executed_trade: null,
          timestamp: '2026-05-14T00:15:00Z',
        },
      })
      emit({
        type: 'step_batch',
        data: {
          step: 3,
          generation: 1,
          price: 30003,
          requested_direction: 'HOLD',
          requested_size_percent: 0,
          transaction_outcome: 'NO_TRANSACTION',
          is_transaction: false,
          position_before: 0.25,
          position_after: 0.25,
          executed_delta: 0,
          position: 0.25,
          balance: 10005,
          pnl: 5,
          rolling_reward: 0,
          steps_per_second: 100,
          equity_curve: [10005, 10005],
          cost: 0,
          cumulative_buys: 1,
          cumulative_sells: 0,
          transaction_distribution: { buy: 1, sell: 0, no_transaction: 2 },
          trade_win_rate: 0,
          winning_trades: 0,
          losing_trades: 0,
          flat_trades: 0,
          executed_trade: null,
          timestamp: '2026-05-14T00:30:00Z',
        },
      })
    })

    expect(result.current.profitLossDistribution).toEqual({ profit: 1, loss: 1, flat: 1 })
  })

  it('resets rolling step outcome distribution when the scope key changes', async () => {
    const { result, rerender } = renderHook(({ scopeKey }: { scopeKey: string | null }) => useTrainingStream(scopeKey), {
      initialProps: { scopeKey: 'run-1' },
    })
    await act(async () => {
      await Promise.resolve()
    })

    act(() => {
      emit({
        type: 'step_batch',
        data: {
          step: 1,
          generation: 1,
          price: 30001,
          requested_direction: 'BUY',
          requested_size_percent: 0.25,
          transaction_outcome: 'BUY',
          is_transaction: true,
          position_before: 0,
          position_after: 0.25,
          executed_delta: 0.25,
          position: 0.25,
          balance: 10010,
          pnl: 10,
          rolling_reward: 0.2,
          steps_per_second: 100,
          equity_curve: [10000, 10010],
          cost: 0.001,
          cumulative_buys: 1,
          cumulative_sells: 0,
          transaction_distribution: { buy: 1, sell: 0, no_transaction: 0 },
          trade_win_rate: 0,
          winning_trades: 0,
          losing_trades: 0,
          flat_trades: 0,
          executed_trade: null,
          timestamp: '2026-05-14T00:00:00Z',
        },
      })
    })

    expect(result.current.profitLossDistribution).toEqual({ profit: 1, loss: 0, flat: 0 })

    rerender({ scopeKey: 'run-2' })

    expect(result.current.profitLossDistribution).toEqual({ profit: 0, loss: 0, flat: 0 })
    expect(result.current.priceBuffer).toEqual([])
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
