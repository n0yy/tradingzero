import { useState } from 'react'
import { ChevronDown, ChevronUp } from 'lucide-react'

import type { TrainingUpdate } from '@/hooks/useTrainingStream'
import { formatSharpe } from '@/lib/format'
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'

function formatMetric(value: number | null | undefined): string {
  if (value === null || value === undefined || Number.isNaN(value)) return '—'
  return value.toLocaleString('en-US')
}

export function PromotionCheckPanel({ event }: { event: TrainingUpdate | null }) {
  const [detailsOpen, setDetailsOpen] = useState(false)

  const promoted = event?.promoted ?? null
  const headline = promoted === null ? 'Not promoted' : promoted ? 'Promoted' : 'Not promoted'
  const summary =
    event?.promotion_gate_reasons?.[0] ??
    (promoted === true
      ? 'Latest generation passed all promotion checks.'
      : 'Latest generation has not passed all promotion checks yet.')

  const checks = event?.promotion_gate_checks ?? []
  const evaluationSharpe = event?.evaluation_sharpe ?? null
  const bestEvaluationSharpe = event?.best_evaluation_sharpe ?? null
  const executedTrades = event?.evaluation_executed_trade_count ?? null
  const sellRealizedExits = event?.evaluation_sell_realized_exit_count ?? null
  const trainingSharpe = event?.training_sharpe ?? null

  return (
    <article className="rounded-xl border border-border/60 bg-card p-4">
      <h2 className="font-display text-lg">Promotion Check</h2>
      <p className={`mt-2 text-sm font-semibold ${promoted ? 'text-(--gain)' : 'text-(--loss)'}`}>{headline}</p>
      <p className="mt-1 text-sm text-muted-foreground" data-testid="promotion-summary">
        {summary}
      </p>

      <div className="mt-3 grid grid-cols-2 gap-2 text-sm">
        <div className="rounded-md border border-border/60 p-2">
          <p className="text-xs text-muted-foreground">Evaluation Sharpe</p>
          <p data-testid="promotion-evaluation-sharpe">{formatSharpe(evaluationSharpe)}</p>
        </div>
        <div className="rounded-md border border-border/60 p-2">
          <p className="text-xs text-muted-foreground">Best Evaluation Sharpe</p>
          <p data-testid="promotion-best-evaluation-sharpe">{formatSharpe(bestEvaluationSharpe)}</p>
        </div>
        <div className="rounded-md border border-border/60 p-2">
          <p className="text-xs text-muted-foreground">Executed Trade Count</p>
          <p data-testid="promotion-executed-trades">{formatMetric(executedTrades)}</p>
        </div>
        <div className="rounded-md border border-border/60 p-2">
          <p className="text-xs text-muted-foreground">SELL Realized Exits</p>
          <p data-testid="promotion-sell-exits">{formatMetric(sellRealizedExits)}</p>
        </div>
      </div>

      <div className="mt-3 space-y-2">
        {checks.length ? (
          checks.map((check) => (
            <div key={check.name} className="rounded-md border border-border/60 p-2 text-sm">
              <div className="flex items-center justify-between gap-2">
                <span className="font-medium">{check.message}</span>
                <span className={check.passed ? 'text-(--gain)' : 'text-(--loss)'}>{check.passed ? 'Pass' : 'Fail'}</span>
              </div>
              <div className="mt-1 text-xs text-muted-foreground">
                Actual: {formatMetric(check.actual)} | Target: {formatMetric(check.target)}
              </div>
            </div>
          ))
        ) : (
          <p className="text-sm text-muted-foreground">No promotion gate checks yet.</p>
        )}
      </div>

      <p className="mt-3 text-xs text-muted-foreground">Training Sharpe (context): {formatSharpe(trainingSharpe)}</p>

      <Collapsible open={detailsOpen} onOpenChange={setDetailsOpen} className="mt-3">
        <CollapsibleTrigger className="inline-flex items-center gap-2 text-sm font-medium text-foreground">
          Per-anchor detail
          {detailsOpen ? <ChevronUp className="size-4" /> : <ChevronDown className="size-4" />}
        </CollapsibleTrigger>
        <CollapsibleContent className="mt-2">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Anchor</TableHead>
                <TableHead>Eval Sharpe</TableHead>
                <TableHead>Executed Trades</TableHead>
                <TableHead>SELL Exits</TableHead>
                <TableHead>Result</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              <TableRow>
                <TableCell data-testid="promotion-anchor-label">Latest Generation #{event?.generation ?? '—'}</TableCell>
                <TableCell>{formatSharpe(evaluationSharpe)}</TableCell>
                <TableCell>{formatMetric(executedTrades)}</TableCell>
                <TableCell>{formatMetric(sellRealizedExits)}</TableCell>
                <TableCell>{headline}</TableCell>
              </TableRow>
            </TableBody>
          </Table>
        </CollapsibleContent>
      </Collapsible>
    </article>
  )
}
