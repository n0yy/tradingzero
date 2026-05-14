import type { TrainingUpdate } from '@/hooks/useTrainingStream'
import { cn } from '@/lib/utils'

type Row = {
  label: 'BUY' | 'HOLD' | 'SELL'
  count: number
  testId: string
  barClass: string
}

function DistributionRow({ row, total }: { row: Row; total: number }) {
  const pct = total > 0 ? (row.count / total) * 100 : 0
  return (
    <div className="grid grid-cols-[60px_1fr_3rem] items-center gap-2">
      <span className="text-xs font-medium text-muted-foreground">{row.label}</span>
      <div className="h-2 overflow-hidden rounded-full bg-secondary">
        <div className={cn('h-full rounded-full', row.barClass)} style={{ width: `${pct}%` }} />
      </div>
      <span data-testid={row.testId} className="text-right text-sm font-medium tabular-nums">
        {row.count}
      </span>
    </div>
  )
}

export function ActionDistributionPanel({ event }: { event: TrainingUpdate | null }) {
  return (
    <article className="card panel">
      <h2>Action Distribution</h2>
      {event === null ? (
        <p data-testid="distribution-empty" className="text-sm text-muted-foreground">
          No live distribution yet — counts appear once a Run streams updates.
        </p>
      ) : (
        <div className="grid gap-3">
          <div className="grid gap-2">
            <DistributionRow
              row={{ label: 'BUY', count: event.action_distribution.buy, testId: 'distribution-buy', barClass: 'bg-(--gain)' }}
              total={event.action_distribution.buy + event.action_distribution.hold + event.action_distribution.sell}
            />
            <DistributionRow
              row={{ label: 'HOLD', count: event.action_distribution.hold, testId: 'distribution-hold', barClass: 'bg-muted-foreground/40' }}
              total={event.action_distribution.buy + event.action_distribution.hold + event.action_distribution.sell}
            />
            <DistributionRow
              row={{ label: 'SELL', count: event.action_distribution.sell, testId: 'distribution-sell', barClass: 'bg-(--loss)' }}
              total={event.action_distribution.buy + event.action_distribution.hold + event.action_distribution.sell}
            />
          </div>
          <dl className="grid grid-cols-2 gap-x-3 border-t border-border pt-2 text-xs">
            <dt className="text-muted-foreground">Cumulative BUY</dt>
            <dd data-testid="cumulative-buys" className="text-right font-medium tabular-nums">
              {event.cumulative_buys}
            </dd>
            <dt className="text-muted-foreground">Cumulative SELL</dt>
            <dd data-testid="cumulative-sells" className="text-right font-medium tabular-nums">
              {event.cumulative_sells}
            </dd>
          </dl>
        </div>
      )}
    </article>
  )
}
