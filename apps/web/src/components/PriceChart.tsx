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
    background: read('--card', '#101f1c'),
    text: read('--muted-foreground', '#7ca099'),
    grid: read('--border', '#16322d'),
    accent: read('--gain', '#2ee6b8'),
  }
}

function PriceChart({ event, priceBuffer, height = 420 }: Props) {
  const ref = useRef<HTMLDivElement | null>(null)
  const seriesRef = useRef<ISeriesApi<'Line'> | null>(null)

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

    const series = chart.addSeries(LineSeries, { color: theme.accent, lineWidth: 2 })
    seriesRef.current = series

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
    if (!seriesRef.current) return
    const lineData = chartData.series.map(
      (p) => ({ time: p.time as unknown as UTCTimestamp, value: p.value }) as LineData,
    )
    seriesRef.current.setData(lineData)
    const markers = chartData.markers.map((m) => ({
      ...m,
      time: m.time as unknown as UTCTimestamp,
    }))
    createSeriesMarkers(seriesRef.current, markers)
  }, [chartData])

  return <div ref={ref} aria-label="price-chart" data-testid="price-chart" />
}

export default PriceChart
