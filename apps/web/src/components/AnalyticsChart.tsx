import type { CSSProperties } from 'react'
import ReactECharts from 'echarts-for-react'

import type { ProfitLossDistribution } from '@/hooks/useTrainingStream'
import { toProfitLossOptions } from '../lib/chart-adapters'

type Props = {
  distribution: ProfitLossDistribution
}

function AnalyticsChart({ distribution }: Props) {
  const total = distribution.profit + distribution.loss + distribution.flat
  const items = [
    { label: 'Profit', value: distribution.profit, color: '#2ee6b8' },
    { label: 'Loss', value: distribution.loss, color: '#ff6b6b' },
    { label: 'Flat', value: distribution.flat, color: '#7ca099' },
  ]

  const formatShare = (value: number) => {
    if (total === 0) return '0%'
    return `${Math.round((value / total) * 100)}%`
  }

  return (
    <div className="analytics-layout" aria-label="analytics-chart">
      <div className="analytics-summary" aria-label="profit-loss-summary">
        {items.map((item) => (
          <div key={item.label} className="analytics-stat">
            <span className="analytics-swatch" style={{ '--swatch': item.color } as CSSProperties} />
            <div className="analytics-copy">
              <strong>{item.label}</strong>
              <span>{formatShare(item.value)} of tracked steps</span>
            </div>
            <b>{item.value}</b>
          </div>
        ))}
      </div>

      <div className="analytics-chart-shell">
        <ReactECharts option={toProfitLossOptions(distribution)} style={{ height: 320, width: '100%' }} />
      </div>
    </div>
  )
}

export default AnalyticsChart
