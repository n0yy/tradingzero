import { useEffect, useMemo, useRef } from 'react'
import {
  LineSeries,
  createChart,
  createSeriesMarkers,
  type ISeriesApi,
  type LineData,
  type UTCTimestamp,
} from 'lightweight-charts'

import { fromPriceBuffer, toPriceChartData } from '../lib/chart-adapters'
import type { PriceBufferPoint, TrainingUpdate } from '../hooks/useTrainingStream'

type Props = {
  event: TrainingUpdate | null
  priceBuffer?: PriceBufferPoint[]
  height?: number
}

function readChartTheme(el: HTMLElement) {
  const styles = getComputedStyle(el)
  const read = (name: string, fallback: string) => {
    const value = styles.getPropertyValue(name).trim()
    if (!value) return fallback
    if (/^(oklch|lch|lab|color)\(/i.test(value)) return fallback
    return value
  }
  return {
    background: read('--card', '#ffffff'),
    text: read('--muted-foreground', '#64748b'),
    grid: read('--border', '#e8e8e8'),
    training: read('--gain', '#25ced1'),
    evaluation: '#f59e0b',
  }
}

function PriceChart({ event, priceBuffer, height = 420 }: Props) {
  const ref = useRef<HTMLDivElement | null>(null)
  const trainSeriesRef = useRef<ISeriesApi<'Line'> | null>(null)
  const evalSeriesRef = useRef<ISeriesApi<'Line'> | null>(null)

  const chartData = useMemo(
    () => (priceBuffer && priceBuffer.length > 0 ? fromPriceBuffer(priceBuffer) : toPriceChartData(event)),
    [event, priceBuffer],
  )

  useEffect(() => {
    if (!ref.current) return

    const theme = readChartTheme(ref.current)
    const chart = createChart(ref.current, {
      layout: { background: { color: theme.background }, textColor: theme.text },
      grid: { vertLines: { color: theme.grid }, horzLines: { color: theme.grid } },
      width: ref.current.clientWidth,
      height,
      rightPriceScale: { borderColor: theme.grid },
      timeScale: { borderColor: theme.grid },
    })

    trainSeriesRef.current = chart.addSeries(LineSeries, {
      color: theme.training,
      lineWidth: 2,
      title: 'Training',
    })
    evalSeriesRef.current = chart.addSeries(LineSeries, {
      color: theme.evaluation,
      lineWidth: 2,
      title: 'Evaluation',
    })

    const ro = new ResizeObserver(() => {
      if (ref.current) chart.applyOptions({ width: ref.current.clientWidth })
    })
    ro.observe(ref.current)

    return () => {
      ro.disconnect()
      chart.remove()
    }
  }, [height])

  useEffect(() => {
    if (!trainSeriesRef.current || !evalSeriesRef.current) return

    const trainPoints = chartData.series.filter((p) => p.phase !== 'evaluation')
    const evalPoints = chartData.series.filter((p) => p.phase === 'evaluation')

    const toLineData = (pts: typeof chartData.series): LineData[] =>
      pts.map((p) => ({ time: p.time as unknown as UTCTimestamp, value: p.value }))

    trainSeriesRef.current.setData(toLineData(trainPoints))
    evalSeriesRef.current.setData(toLineData(evalPoints))

    const trainMarkers = chartData.markers
      .filter((m) => {
        const pt = chartData.series.find((p) => p.time === m.time)
        return pt?.phase !== 'evaluation'
      })
      .map((m) => ({ ...m, time: m.time as unknown as UTCTimestamp }))

    const evalMarkers = chartData.markers
      .filter((m) => {
        const pt = chartData.series.find((p) => p.time === m.time)
        return pt?.phase === 'evaluation'
      })
      .map((m) => ({ ...m, time: m.time as unknown as UTCTimestamp }))

    createSeriesMarkers(trainSeriesRef.current, trainMarkers)
    createSeriesMarkers(evalSeriesRef.current, evalMarkers)
  }, [chartData])

  return (
    <div className="relative">
      <div className="absolute right-3 top-3 z-10 flex items-center gap-3 text-xs text-muted-foreground">
        <span className="flex items-center gap-1">
          <span className="inline-block h-2 w-4 rounded-sm" style={{ background: '#25ced1' }} />
          Training
        </span>
        <span className="flex items-center gap-1">
          <span className="inline-block h-2 w-4 rounded-sm" style={{ background: '#f59e0b' }} />
          Evaluation
        </span>
      </div>
      <div ref={ref} aria-label="price-chart" data-testid="price-chart" />
    </div>
  )
}

export default PriceChart
