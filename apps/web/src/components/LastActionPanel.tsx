import { ActionBadge } from './ActionBadge'
import type { TrainingUpdate } from '@/hooks/useTrainingStream'
import { formatSignedUsd, formatUsd } from '@/lib/format'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'

function formatTimestamp(iso: string | null): string {
  if (!iso) return '—'
  const d = new Date(iso)
  return d.toLocaleString()
}

export function LastActionPanel({ event }: { event: TrainingUpdate | null }) {
  const lastTransaction = event?.last_transaction ?? null

  return (
    <Card>
      <CardHeader>
        <CardTitle className="font-semibold">Last Transaction</CardTitle>
      </CardHeader>
      <CardContent>
        {lastTransaction === null ? (
          <p data-testid="last-transaction-empty" className="text-sm text-muted-foreground">
            No live transaction yet — start a Run to see the latest executed trade.
          </p>
        ) : (
          <div className="grid gap-2">
            <div className="flex items-center justify-between">
              <ActionBadge action={lastTransaction.action} testId="last-transaction-direction" />
              <span className="text-xs text-muted-foreground">{formatTimestamp(lastTransaction.timestamp)}</span>
            </div>
            <dl className="grid grid-cols-2 gap-x-3 gap-y-1 text-sm">
              <dt className="text-muted-foreground">Price</dt>
              <dd data-testid="last-transaction-price" className="text-right font-medium">
                {formatUsd(lastTransaction.execution_price)}
              </dd>
              <dt className="text-muted-foreground">Size</dt>
              <dd className="text-right font-medium">{(lastTransaction.size_percent * 100).toFixed(0)}%</dd>
              <dt className="text-muted-foreground">Position</dt>
              <dd className="text-right font-medium">
                {lastTransaction.position_before.toFixed(2)} → {lastTransaction.position_after.toFixed(2)}
              </dd>
              <dt className="text-muted-foreground">Balance</dt>
              <dd className="text-right font-medium">{formatUsd(lastTransaction.balance_after)}</dd>
              <dt className="text-muted-foreground">Unrealized PnL</dt>
              <dd className="text-right font-medium">{formatSignedUsd(lastTransaction.unrealized_pnl_after)}</dd>
            </dl>
          </div>
        )}
      </CardContent>
    </Card>
  )
}
