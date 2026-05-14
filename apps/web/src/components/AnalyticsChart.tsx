import ReactECharts from 'echarts-for-react'

import { type TrendPoint, toEchartsOptions } from '../lib/chart-adapters'

type Props = {
  points: TrendPoint[]
}

function AnalyticsChart({ points }: Props) {
  return (
    <div className="chart-card analytics-card" aria-label="analytics-chart">
      <ReactECharts option={toEchartsOptions(points)} style={{ height: 260, width: '100%' }} />
    </div>
  )
}

export default AnalyticsChart
