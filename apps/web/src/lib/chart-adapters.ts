import type { PriceBufferPoint, ProfitLossDistribution, TrainingUpdate } from '../hooks/useTrainingStream'

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
  const last = stream.last_transaction
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

export function toProfitLossOptions(distribution: ProfitLossDistribution) {
  const data = [
    { name: 'Profit', value: distribution.profit, itemStyle: { color: '#2ee6b8' } },
    { name: 'Loss', value: distribution.loss, itemStyle: { color: '#ff6b6b' } },
    { name: 'Flat', value: distribution.flat, itemStyle: { color: '#7ca099' } },
  ]
  const total = distribution.profit + distribution.loss + distribution.flat

  return {
    backgroundColor: 'transparent',
    tooltip: {
      trigger: 'item',
      formatter: '{b}: {c} steps',
    },
    graphic: [
      {
        type: 'text',
        left: 'center',
        top: '41%',
        style: {
          text: String(total),
          fill: '#e5f4ef',
          fontSize: 34,
          fontWeight: 700,
          textAlign: 'center',
        },
      },
      {
        type: 'text',
        left: 'center',
        top: '55%',
        style: {
          text: 'Tracked Steps',
          fill: '#7ca099',
          fontSize: 13,
          textAlign: 'center',
        },
      },
    ],
    series: [
      {
        name: 'Step Outcome',
        type: 'pie',
        radius: ['60%', '82%'],
        center: ['50%', '48%'],
        avoidLabelOverlap: true,
        label: { show: false },
        labelLine: { show: false },
        itemStyle: {
          borderColor: '#101f1c',
          borderWidth: 6,
        },
        data,
      },
    ],
  }
}
