import { useEffect, useRef, useState } from 'react'

export type TrainingUpdate = {
  generation: number
  current_sharpe: number
  best_sharpe: number
  balance: number
  pnl: number
  win_rate: number
  progress: number
  action_distribution: { buy: number; hold: number; sell: number }
  cumulative_buys: number
  cumulative_sells: number
  last_action: {
    action: 'BUY' | 'SELL' | 'HOLD'
    timestamp: string
    execution_price: number
    size_percent: number
    position_before: number
    position_after: number
    notional_usd: number
    balance_before: number
    balance_after: number
    fee: number
    unrealized_pnl_after: number
  }
}

export type StepBatch = {
  step: number
  generation: number
  price: number
  last_action: 'BUY' | 'SELL' | 'HOLD'
  position: number
  balance: number
  pnl: number
  rolling_reward: number
  steps_per_second: number
  equity_curve: number[]
  timestamp: string
}

export type PriceBufferPoint = { time: number; value: number; action: 'BUY' | 'SELL' | 'HOLD' }

const PRICE_BUFFER_MAX = 500
const RECONNECT_DELAY_MS = 500

function incrementActionDistribution(
  current: TrainingUpdate['action_distribution'],
  action: StepBatch['last_action'],
): TrainingUpdate['action_distribution'] {
  return {
    buy: current.buy + (action === 'BUY' ? 1 : 0),
    hold: current.hold + (action === 'HOLD' ? 1 : 0),
    sell: current.sell + (action === 'SELL' ? 1 : 0),
  }
}

function mergeStepIntoEvent(previous: TrainingUpdate | null, data: StepBatch): TrainingUpdate {
  const sameGeneration = previous?.generation === data.generation
  const previousPosition = previous?.last_action.position_after ?? 0
  const actionDistribution = incrementActionDistribution(
    sameGeneration ? previous.action_distribution : { buy: 0, hold: 0, sell: 0 },
    data.last_action,
  )

  return {
    generation: data.generation,
    current_sharpe: previous?.current_sharpe ?? Number.NaN,
    best_sharpe: previous?.best_sharpe ?? Number.NaN,
    balance: data.balance,
    pnl: data.pnl,
    win_rate: previous?.win_rate ?? Number.NaN,
    progress: previous?.progress ?? Number.NaN,
    action_distribution: actionDistribution,
    cumulative_buys: (sameGeneration ? previous.cumulative_buys : previous?.cumulative_buys ?? 0) + (data.last_action === 'BUY' ? 1 : 0),
    cumulative_sells: (sameGeneration ? previous.cumulative_sells : previous?.cumulative_sells ?? 0) + (data.last_action === 'SELL' ? 1 : 0),
    last_action: {
      action: data.last_action,
      timestamp: data.timestamp,
      execution_price: data.price,
      size_percent: Math.abs(data.position - previousPosition),
      position_before: previousPosition,
      position_after: data.position,
      notional_usd: data.price * Math.abs(data.position - previousPosition),
      balance_before: previous?.balance ?? data.balance,
      balance_after: data.balance,
      fee: 0,
      unrealized_pnl_after: data.pnl,
    },
  }
}

export function useTrainingStream() {
  const [event, setEvent] = useState<TrainingUpdate | null>(null)
  const [stepBatch, setStepBatch] = useState<StepBatch | null>(null)
  const [priceBuffer, setPriceBuffer] = useState<PriceBufferPoint[]>([])
  const [connected, setConnected] = useState(false)
  const bufferRef = useRef<PriceBufferPoint[]>([])
  const reconnectTimerRef = useRef<number | null>(null)

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
          const next = [...bufferRef.current, { time: data.step, value: data.price, action: data.last_action }]
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

  return { event, stepBatch, priceBuffer, connected }
}
