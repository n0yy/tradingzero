import type { StepBatch, TrainingUpdate } from '@/hooks/useTrainingStream'
import { cn } from '@/lib/utils'
import { formatPercent, formatSharpe, formatSignedUsd, formatUsd } from '@/lib/format'

type KpiCellProps = {
  label: string
  value: string
  testId: string
  sign?: 'gain' | 'loss' | null
}

function KpiCell({ label, value, testId, sign }: KpiCellProps) {
  return (
    <article className="card">
      <span>{label}</span>
      <strong
        data-testid={testId}
        data-sign={sign ?? undefined}
        className={cn(sign === 'gain' && 'text-(--gain)', sign === 'loss' && 'text-(--loss)')}
      >
        {value}
      </strong>
    </article>
  )
}

export function KpiStrip({ event, stepBatch }: { event: TrainingUpdate | null; stepBatch?: StepBatch | null }) {
  const sharpe = event?.current_sharpe ?? null
  const bestSharpe = event?.best_sharpe ?? null
  const balance = stepBatch?.balance ?? event?.balance ?? null
  const pnl = stepBatch?.pnl ?? event?.pnl ?? null
  const tradeWinRate = stepBatch?.trade_win_rate ?? event?.trade_win_rate ?? null
  const progress = event?.progress ?? null

  const pnlSign: KpiCellProps['sign'] = pnl === null ? null : pnl >= 0 ? 'gain' : 'loss'

  return (
    <section className="grid metrics">
      <KpiCell label="Sharpe" testId="kpi-sharpe" value={formatSharpe(sharpe)} />
      <KpiCell label="Best Sharpe" testId="kpi-best-sharpe" value={formatSharpe(bestSharpe)} />
      <KpiCell label="Balance" testId="kpi-balance" value={formatUsd(balance)} />
      <KpiCell label="PnL" testId="kpi-pnl" value={formatSignedUsd(pnl)} sign={pnlSign} />
      <KpiCell label="Trade Win Rate" testId="kpi-trade-win-rate" value={formatPercent(tradeWinRate)} />
      <KpiCell label="Progress" testId="kpi-progress" value={formatPercent(progress)} />
    </section>
  )
}
