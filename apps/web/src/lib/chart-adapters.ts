import type { PriceBufferPoint, TrainingUpdate } from '../hooks/useTrainingStream'

export type TrendPoint = { generation: number; sharpe: number; pnl: number }

export type PricePoint = { time: number; value: number }

export type TradeMarker = {
  time: number
  position: 'aboveBar' | 'belowBar'
  color: string
  shape: 'arrowUp' | 'arrowDown'
  text: string
}

export type PriceChartData = {
  series: PricePoint[]
  markers: TradeMarker[]
}

export function toPriceSeries(prices: number[]) {
  return prices.map((value, idx) => ({ time: (idx + 1) as unknown as number, value }))
}

export function toTradeMarkers(actions: number[], prices: number[]) {
  const markers: TradeMarker[] = []

  for (let i = 0; i < actions.length; i += 1) {
    const action = actions[i]
    if (action === 1) {
      markers.push({
        time: i + 1,
        position: 'belowBar',
        color: '#2ee6b8',
        shape: 'arrowUp',
        text: `BUY @ ${prices[i] ?? 0}`,
      })
    }
    if (action === 2) {
      markers.push({
        time: i + 1,
        position: 'aboveBar',
        color: '#ff6b6b',
        shape: 'arrowDown',
        text: `SELL @ ${prices[i] ?? 0}`,
      })
    }
  }

  return markers
}

export function toPriceChartData(stream: TrainingUpdate | null): PriceChartData {
  if (!stream) return { series: [], markers: [] }
  const last = stream.last_action
  if (!last) return { series: [], markers: [] }

  const series: PricePoint[] = [{ time: stream.generation, value: last.execution_price }]
  const markers: TradeMarker[] = []
  if (last.action === 'BUY') {
    markers.push({
      time: stream.generation,
      position: 'belowBar',
      color: '#2ee6b8',
      shape: 'arrowUp',
      text: `BUY @ ${last.execution_price}`,
    })
  } else if (last.action === 'SELL') {
    markers.push({
      time: stream.generation,
      position: 'aboveBar',
      color: '#ff6b6b',
      shape: 'arrowDown',
      text: `SELL @ ${last.execution_price}`,
    })
  }
  return { series, markers }
}

export function fromPriceBuffer(buffer: PriceBufferPoint[]): PriceChartData {
  const series: PricePoint[] = buffer.map((p) => ({ time: p.time, value: p.value }))
  const markers: TradeMarker[] = []
  for (const point of buffer) {
    if (point.action === 'BUY') {
      markers.push({
        time: point.time,
        position: 'belowBar',
        color: '#2ee6b8',
        shape: 'arrowUp',
        text: `BUY @ ${point.value}`,
      })
    } else if (point.action === 'SELL') {
      markers.push({
        time: point.time,
        position: 'aboveBar',
        color: '#ff6b6b',
        shape: 'arrowDown',
        text: `SELL @ ${point.value}`,
      })
    }
  }
  return { series, markers }
}

export function toEchartsOptions(points: TrendPoint[]) {
  return {
    backgroundColor: 'transparent',
    tooltip: { trigger: 'axis' },
    grid: { left: 30, right: 20, top: 20, bottom: 25 },
    xAxis: {
      type: 'category',
      data: points.map((p) => p.generation),
      axisLine: { lineStyle: { color: '#29524a' } },
      axisLabel: { color: '#7ca099' },
    },
    yAxis: [
      { type: 'value', axisLine: { lineStyle: { color: '#29524a' } }, axisLabel: { color: '#7ca099' }, splitLine: { lineStyle: { color: '#17342f' } } },
      { type: 'value', axisLine: { lineStyle: { color: '#29524a' } }, axisLabel: { color: '#7ca099' }, splitLine: { show: false } },
    ],
    series: [
      { name: 'Sharpe', type: 'line', smooth: true, data: points.map((p) => p.sharpe), lineStyle: { color: '#2ee6b8' }, showSymbol: false },
      { name: 'PnL', type: 'bar', yAxisIndex: 1, data: points.map((p) => p.pnl), itemStyle: { color: '#1ea483' } },
    ],
  }
}
