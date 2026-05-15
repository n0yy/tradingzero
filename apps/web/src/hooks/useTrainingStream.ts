import { useEffect, useRef, useState } from 'react'

export type ExecutedTrade = {
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

export type TrainingUpdate = {
  generation: number
  current_sharpe: number
  best_sharpe: number
  balance: number
  pnl: number
  trade_win_rate: number
  progress: number
  transaction_distribution: { buy: number; sell: number; no_transaction: number }
  cumulative_buys: number
  cumulative_sells: number
  winning_trades: number
  losing_trades: number
  flat_trades: number
  last_transaction: ExecutedTrade | null
}

export type StepBatch = {
  step: number
  generation: number
  price: number
  requested_direction: 'BUY' | 'SELL' | 'HOLD'
  requested_size_percent: number
  transaction_outcome: 'BUY' | 'SELL' | 'NO_TRANSACTION'
  is_transaction: boolean
  position_before: number
  position_after: number
  executed_delta: number
  position: number
  balance: number
  pnl: number
  rolling_reward: number
  steps_per_second: number
  equity_curve: number[]
  cost: number
  cumulative_buys: number
  cumulative_sells: number
  transaction_distribution: TrainingUpdate['transaction_distribution']
  trade_win_rate: number
  winning_trades: number
  losing_trades: number
  flat_trades: number
  executed_trade: ExecutedTrade | null
  timestamp: string
}

export type PriceBufferPoint = { time: number; value: number; action: 'BUY' | 'SELL' | 'NO_TRANSACTION' }
export type ProfitLossDistribution = { profit: number; loss: number; flat: number }

const PRICE_BUFFER_MAX = 500
const RECONNECT_DELAY_MS = 500

function emptyProfitLossDistribution(): ProfitLossDistribution {
  return { profit: 0, loss: 0, flat: 0 }
}

function classifyStepOutcome(data: StepBatch): keyof ProfitLossDistribution {
  const curve = data.equity_curve
  if (curve.length < 2) return 'flat'
  const previous = curve[curve.length - 2]
  const current = curve[curve.length - 1]
  if (current > previous) return 'profit'
  if (current < previous) return 'loss'
  return 'flat'
}

function mergeStepIntoEvent(previous: TrainingUpdate | null, data: StepBatch): TrainingUpdate {
  return {
    generation: data.generation,
    current_sharpe: previous?.current_sharpe ?? Number.NaN,
    best_sharpe: previous?.best_sharpe ?? Number.NaN,
    balance: data.balance,
    pnl: data.pnl,
    trade_win_rate: data.trade_win_rate,
    progress: previous?.progress ?? Number.NaN,
    transaction_distribution: data.transaction_distribution,
    cumulative_buys: data.cumulative_buys,
    cumulative_sells: data.cumulative_sells,
    winning_trades: data.winning_trades,
    losing_trades: data.losing_trades,
    flat_trades: data.flat_trades,
    last_transaction: data.executed_trade ?? previous?.last_transaction ?? null,
  }
}

export function useTrainingStream(scopeKey?: string | null) {
  const [event, setEvent] = useState<TrainingUpdate | null>(null)
  const [stepBatch, setStepBatch] = useState<StepBatch | null>(null)
  const [priceBuffer, setPriceBuffer] = useState<PriceBufferPoint[]>([])
  const [profitLossDistribution, setProfitLossDistribution] = useState<ProfitLossDistribution>(emptyProfitLossDistribution)
  const [connected, setConnected] = useState(false)
  const bufferRef = useRef<PriceBufferPoint[]>([])
  const reconnectTimerRef = useRef<number | null>(null)

  useEffect(() => {
    bufferRef.current = []
    setEvent(null)
    setStepBatch(null)
    setPriceBuffer([])
    setProfitLossDistribution(emptyProfitLossDistribution())
  }, [scopeKey])

  useEffect(() => {
    let disposed = false
    let activeSocket: WebSocket | null = null
    const proto = window.location.protocol === 'https:' ? 'wss' : 'ws'
    const streamUrl = `${proto}://${window.location.host}/ws/runs/stream`

    const clearReconnectTimer = () => {
      if (reconnectTimerRef.current === null) return
      window.clearTimeout(reconnectTimerRef.current)
      reconnectTimerRef.current = null
    }

    const scheduleReconnect = () => {
      if (disposed || reconnectTimerRef.current !== null) return
      reconnectTimerRef.current = window.setTimeout(() => {
        reconnectTimerRef.current = null
        connect()
      }, RECONNECT_DELAY_MS)
    }

    const connect = () => {
      if (disposed) return

      const ws = new WebSocket(streamUrl)
      activeSocket = ws

      ws.onopen = () => {
        clearReconnectTimer()
        setConnected(true)
      }
      ws.onclose = () => {
        if (activeSocket === ws) activeSocket = null
        setConnected(false)
        scheduleReconnect()
      }
      ws.onmessage = (msg) => {
        const parsed = JSON.parse(msg.data)
        if (parsed.type === 'training_update') {
          setEvent(parsed.data as TrainingUpdate)
          return
        }
        if (parsed.type === 'step_batch') {
          const data = parsed.data as StepBatch
          setStepBatch(data)
          setEvent((current) => mergeStepIntoEvent(current, data))
          setProfitLossDistribution((current) => {
            const key = classifyStepOutcome(data)
            return { ...current, [key]: current[key] + 1 }
          })
          const next = [...bufferRef.current, { time: data.step, value: data.price, action: data.transaction_outcome }]
          bufferRef.current = next.length > PRICE_BUFFER_MAX ? next.slice(next.length - PRICE_BUFFER_MAX) : next
          setPriceBuffer(bufferRef.current)
        }
      }
    }

    connect()

    return () => {
      disposed = true
      clearReconnectTimer()
      activeSocket?.close()
    }
  }, [])

  return { event, stepBatch, priceBuffer, profitLossDistribution, connected }
}
