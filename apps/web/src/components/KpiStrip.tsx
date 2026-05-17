import type { StepBatch, TrainingUpdate } from '@/hooks/useTrainingStream'
import { cn } from '@/lib/utils'
import { formatPercent, formatSignedUsd, formatUsd } from '@/lib/format'
import { Card, CardContent } from '@/components/ui/card'

type KpiCellProps = {
  label: string
  value: string
  testId: string
  sign?: 'gain' | 'loss' | null
}

function KpiCell({ label, value, testId, sign }: KpiCellProps) {
  return (
    <Card>
      <CardContent className="px-4">
        <span className="text-xs text-muted-foreground">{label}</span>
        <strong
          data-testid={testId}
          data-sign={sign ?? undefined}
          className={cn(
            'mt-1 block text-xl font-semibold tabular-nums',
            sign === 'gain' && 'text-(--gain)',
            sign === 'loss' && 'text-(--loss)',
          )}
        >
          {value}
        </strong>
      </CardContent>
    </Card>
  )
}

export function KpiStrip({ event, stepBatch }: { event: TrainingUpdate | null; stepBatch?: StepBatch | null }) {
  const balance = stepBatch?.balance ?? event?.balance ?? null
  const pnl = stepBatch?.pnl ?? event?.pnl ?? null
  const tradeWinRate = stepBatch?.trade_win_rate ?? event?.trade_win_rate ?? null
  const progress = event?.progress ?? null

  const pnlSign: KpiCellProps['sign'] = pnl === null ? null : pnl >= 0 ? 'gain' : 'loss'

  return (
    <section className="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-4">
      <KpiCell label="Balance" testId="kpi-balance" value={formatUsd(balance)} />
      <KpiCell label="PnL" testId="kpi-pnl" value={formatSignedUsd(pnl)} sign={pnlSign} />
      <KpiCell label="Trade Win Rate" testId="kpi-trade-win-rate" value={formatPercent(tradeWinRate)} />
      <KpiCell label="Progress" testId="kpi-progress" value={formatPercent(progress)} />
    </section>
  )
}
