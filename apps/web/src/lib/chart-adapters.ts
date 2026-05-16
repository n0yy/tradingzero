import type { PriceBufferPoint, ProfitLossDistribution, TrainingUpdate } from '../hooks/useTrainingStream'

export type PricePoint = { time: number; value: number; phase: 'training' | 'evaluation' }

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
  return prices.map((value, idx) => ({ time: (idx + 1) as unknown as number, value, phase: 'training' as const }))
}

export function toTradeMarkers(actions: number[], prices: number[]) {
  const markers: TradeMarker[] = []

  for (let i = 0; i < actions.length; i += 1) {
    const action = actions[i]
    if (action === 1) {
      markers.push({
        time: i + 1,
        position: 'belowBar',
        color: '#25ced1',
        shape: 'arrowUp',
        text: `BUY @ ${prices[i] ?? 0}`,
      })
    }
    if (action === 2) {
      markers.push({
        time: i + 1,
        position: 'aboveBar',
        color: '#ea526f',
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

  const series: PricePoint[] = [{ time: stream.generation, value: last.execution_price, phase: 'training' as const }]
  const markers: TradeMarker[] = []
  if (last.action === 'BUY') {
    markers.push({
      time: stream.generation,
      position: 'belowBar',
      color: '#25ced1',
      shape: 'arrowUp',
      text: `BUY @ ${last.execution_price}`,
    })
  } else if (last.action === 'SELL') {
    markers.push({
      time: stream.generation,
      position: 'aboveBar',
      color: '#ea526f',
      shape: 'arrowDown',
      text: `SELL @ ${last.execution_price}`,
    })
  }
  return { series, markers }
}

export function fromPriceBuffer(buffer: PriceBufferPoint[]): PriceChartData {
  const series: PricePoint[] = buffer.map((p) => ({ time: p.time, value: p.value, phase: p.phase ?? 'training' }))
  const markers: TradeMarker[] = []
  for (const point of buffer) {
    if (point.action === 'BUY') {
      markers.push({
        time: point.time,
        position: 'belowBar',
        color: '#25ced1',
        shape: 'arrowUp',
        text: `BUY @ ${point.value}`,
      })
    } else if (point.action === 'SELL') {
      markers.push({
        time: point.time,
        position: 'aboveBar',
        color: '#ea526f',
        shape: 'arrowDown',
        text: `SELL @ ${point.value}`,
      })
    }
  }
  return { series, markers }
}

export function toProfitLossOptions(distribution: ProfitLossDistribution) {
  const data = [
    { name: 'Profit', value: distribution.profit, itemStyle: { color: '#25ced1' } },
    { name: 'Loss', value: distribution.loss, itemStyle: { color: '#ea526f' } },
    { name: 'Flat', value: distribution.flat, itemStyle: { color: '#64748b' } },
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
          fill: '#1a1a2e',
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
          fill: '#64748b',
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
          borderColor: '#ffffff',
          borderWidth: 6,
        },
        data,
      },
    ],
  }
}
