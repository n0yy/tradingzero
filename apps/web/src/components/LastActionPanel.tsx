import { ActionBadge } from './ActionBadge'
import type { TrainingUpdate } from '@/hooks/useTrainingStream'
import { formatSignedUsd, formatUsd } from '@/lib/format'

function formatTimestamp(iso: string | null): string {
  if (!iso) return '—'
  const d = new Date(iso)
  return d.toLocaleString()
}

export function LastActionPanel({ event }: { event: TrainingUpdate | null }) {
  return (
    <article className="card panel">
      <h2>Last Action</h2>
      {event === null ? (
        <p data-testid="last-action-empty" className="text-sm text-muted-foreground">
          No live action yet — start a Run to see the latest agent decision.
        </p>
      ) : (
        <div className="grid gap-2">
          <div className="flex items-center justify-between">
            <ActionBadge action={event.last_action.action} testId="last-action-direction" />
            <span className="text-xs text-muted-foreground">{formatTimestamp(event.last_action.timestamp)}</span>
          </div>
          <dl className="grid grid-cols-2 gap-x-3 gap-y-1 text-sm">
            <dt className="text-muted-foreground">Price</dt>
            <dd data-testid="last-action-price" className="text-right font-medium">
              {formatUsd(event.last_action.execution_price)}
            </dd>
            <dt className="text-muted-foreground">Size</dt>
            <dd className="text-right font-medium">{(event.last_action.size_percent * 100).toFixed(0)}%</dd>
            <dt className="text-muted-foreground">Position</dt>
            <dd className="text-right font-medium">
              {event.last_action.position_before.toFixed(2)} → {event.last_action.position_after.toFixed(2)}
            </dd>
            <dt className="text-muted-foreground">Balance</dt>
            <dd className="text-right font-medium">{formatUsd(event.last_action.balance_after)}</dd>
            <dt className="text-muted-foreground">Unrealized PnL</dt>
            <dd className="text-right font-medium">{formatSignedUsd(event.last_action.unrealized_pnl_after)}</dd>
          </dl>
        </div>
      )}
    </article>
  )
}
