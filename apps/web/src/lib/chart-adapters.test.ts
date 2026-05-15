import { describe, expect, it } from 'vitest'

import {
  fromPriceBuffer,
  toProfitLossOptions,
  toPriceChartData,
  toPriceSeries,
  toTradeMarkers,
  type PriceChartData,
} from './chart-adapters'
import type { TrainingUpdate } from '../hooks/useTrainingStream'

const fakeUpdate = (overrides: Partial<TrainingUpdate> = {}): TrainingUpdate => ({
  generation: 1,
  training_sharpe: 0.1,
  evaluation_sharpe: 0.1,
  best_evaluation_sharpe: 0.2,
  balance: 10000,
  pnl: 0,
  trade_win_rate: 0.5,
  progress: 0.1,
  transaction_distribution: { buy: 0, sell: 0, no_transaction: 0 },
  cumulative_buys: 0,
  cumulative_sells: 0,
  winning_trades: 0,
  losing_trades: 0,
  flat_trades: 0,
  last_transaction: {
    action: 'BUY',
    timestamp: '2026-05-14T00:00:00Z',
    execution_price: 100,
    size_percent: 0.25,
    position_before: 0,
    position_after: 0.25,
    notional_usd: 2500,
    balance_before: 10000,
    balance_after: 10000,
    fee: 0,
    realized_pnl: 0,
    unrealized_pnl_after: 0,
  },
  ...overrides,
})

describe('chart adapters', () => {
  it('maps price series to lightweight-chart points', () => {
    const points = toPriceSeries([100, 102.5, 101])
    expect(points).toHaveLength(3)
    expect(points[0].value).toBe(100)
    expect(points[2].value).toBe(101)
  })

  it('maps action series to buy/sell markers only', () => {
    const markers = toTradeMarkers([1, 0, 2], [100, 101, 99])
    expect(markers).toHaveLength(2)
    expect(markers[0].text).toContain('BUY')
    expect(markers[1].text).toContain('SELL')
  })

  it('creates echarts option for analytics', () => {
    const option = toProfitLossOptions({ profit: 12, loss: 5, flat: 3 })
    expect(option.series).toHaveLength(1)
  })
})

describe('toPriceChartData', () => {
  it('returns empty data when stream is null', () => {
    const result: PriceChartData = toPriceChartData(null)
    expect(result.series).toHaveLength(0)
    expect(result.markers).toHaveLength(0)
  })

  it('extracts a single price point from the last transaction', () => {
    const result = toPriceChartData(fakeUpdate({ last_transaction: { ...fakeUpdate().last_transaction!, action: 'BUY', execution_price: 100 } }))
    expect(result.series).toHaveLength(1)
    expect(result.series[0].value).toBe(100)
  })

  it('emits a BUY marker when last_transaction is BUY', () => {
    const result = toPriceChartData(
      fakeUpdate({
        last_transaction: { ...fakeUpdate().last_transaction!, action: 'BUY', execution_price: 105 },
      }),
    )
    expect(result.markers).toHaveLength(1)
    expect(result.markers[0].text).toContain('BUY')
  })

  it('emits a SELL marker when last_transaction is SELL', () => {
    const result = toPriceChartData(
      fakeUpdate({
        last_transaction: { ...fakeUpdate().last_transaction!, action: 'SELL', execution_price: 99 },
      }),
    )
    expect(result.markers).toHaveLength(1)
    expect(result.markers[0].text).toContain('SELL')
  })
})

describe('fromPriceBuffer', () => {
  it('returns empty data when buffer is empty', () => {
    expect(fromPriceBuffer([])).toEqual({ series: [], markers: [] })
  })

  it('maps each buffer point to a price series point', () => {
    const result = fromPriceBuffer([
      { time: 1, value: 30000, action: 'NO_TRANSACTION' },
      { time: 2, value: 30050, action: 'BUY' },
      { time: 3, value: 30025, action: 'NO_TRANSACTION' },
    ])
    expect(result.series).toHaveLength(3)
    expect(result.series[0].value).toBe(30000)
    expect(result.series.at(-1)?.value).toBe(30025)
  })

  it('emits markers for BUY and SELL actions only', () => {
    const result = fromPriceBuffer([
      { time: 1, value: 30000, action: 'BUY' },
      { time: 2, value: 30050, action: 'NO_TRANSACTION' },
      { time: 3, value: 29900, action: 'SELL' },
    ])
    expect(result.markers).toHaveLength(2)
    expect(result.markers[0].text).toContain('BUY')
    expect(result.markers[1].text).toContain('SELL')
  })
})
