import { useMutation, useQuery } from '@tanstack/react-query'

import { ActionBadge } from '@/components/ActionBadge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { fetchActiveConfig, runBestBattle } from '@/lib/api'
import { formatPercent, formatSignedUsd, formatUsd } from '@/lib/format'
import { useUIStore } from '@/store/ui'

function formatTimestamp(iso: string | null, mode: 'utc' | 'local'): string {
  if (!iso) return '—'
  const d = new Date(iso)
  return mode === 'utc' ? d.toISOString() : d.toLocaleString()
}

function KpiCard({ label, value, testId }: { label: string; value: string; testId: string }) {
  return (
    <Card>
      <CardContent className="px-4 pb-3 pt-4">
        <span className="text-xs text-muted-foreground">{label}</span>
        <strong data-testid={testId} className="mt-1 block text-xl font-semibold tabular-nums">
          {value}
        </strong>
      </CardContent>
    </Card>
  )
}

export default function BattlePage() {
  const timeMode = useUIStore((s) => s.timeMode)
  const configQuery = useQuery({
    queryKey: ['active-config'],
    queryFn: fetchActiveConfig,
    refetchInterval: 7000,
  })
  const battleMutation = useMutation({
    mutationFn: runBestBattle,
  })

  const result = battleMutation.data
  const checkpointDir = configQuery.data?.config?.self_play.checkpoint_dir ?? 'agent/checkpoints/'
  const checkpointPath = checkpointDir.endsWith('/') ? `${checkpointDir}best.zip` : `${checkpointDir}/best.zip`
  const realizedExitCount = result ? result.winning_trades + result.losing_trades + result.flat_trades : 0
  const battleError = battleMutation.error instanceof Error ? battleMutation.error.message : null

  return (
    <main className="mx-auto w-full max-w-none px-4 py-4 md:px-6">
      <header className="mb-4">
        <div className="flex items-center gap-3">
          <h1 className="font-display text-2xl tracking-wide text-foreground">Battle</h1>
          <span className="inline-flex rounded-full bg-secondary px-3 py-1 text-xs font-medium text-secondary-foreground">
            {battleMutation.isPending ? 'BATTLING' : result ? 'READY' : 'IDLE'}
          </span>
        </div>
        <p className="mt-1 text-sm text-muted-foreground">Run the promoted best.zip once against the latest market slice.</p>
      </header>

      <section className="grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-6">
        <KpiCard label="Checkpoint" value="best.zip" testId="battle-checkpoint" />
        <KpiCard
          label="Market"
          testId="battle-market"
          value={`${configQuery.data?.config?.data.symbol ?? '—'} ${configQuery.data?.config?.data.timeframe ?? ''}`}
        />
        <KpiCard label="Trade Win Rate" testId="battle-win-rate" value={formatPercent(result?.trade_win_rate)} />
        <KpiCard label="Final Balance" testId="battle-final-balance" value={formatUsd(result?.final_balance)} />
        <KpiCard label="PnL" testId="battle-pnl" value={formatSignedUsd(result?.pnl)} />
        <KpiCard label="Total Trades" testId="battle-total-trades" value={result?.total_trades?.toString() ?? '—'} />
      </section>

      <section className="mt-3 grid gap-3 xl:grid-cols-2">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-semibold">Battle Controls</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3 text-sm">
            <p className="text-muted-foreground">Checkpoint: <span className="font-mono text-foreground">{checkpointPath}</span></p>
            <p className="text-muted-foreground">
              Uses the active config for symbol, timeframe, env shape, and episode length, then runs one deterministic inference pass.
            </p>
            <Button
              data-testid="run-battle"
              type="button"
              size="sm"
              onClick={() => battleMutation.mutate()}
              disabled={battleMutation.isPending}
            >
              {battleMutation.isPending ? 'Running Battle...' : 'Run Best Agent'}
            </Button>
            {battleMutation.isError && (
              <p className="text-sm text-destructive" data-testid="battle-error">
                {battleError ?? 'Battle failed. Check that best.zip exists and matches the active environment.'}
              </p>
            )}
            {result && (
              <p className="text-sm text-muted-foreground" data-testid="battle-summary-line">
                {result.total_steps} steps · {result.winning_trades}/{realizedExitCount} winning realized exits.
              </p>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-semibold">Outcome Summary</CardTitle>
          </CardHeader>
          <CardContent>
            {result ? (
              <dl className="grid grid-cols-2 gap-x-3 gap-y-1 text-sm">
                <dt className="text-muted-foreground">Winning exits</dt>
                <dd className="text-right font-medium">{result.winning_trades}</dd>
                <dt className="text-muted-foreground">Losing exits</dt>
                <dd className="text-right font-medium">{result.losing_trades}</dd>
                <dt className="text-muted-foreground">Flat exits</dt>
                <dd className="text-right font-medium">{result.flat_trades}</dd>
                <dt className="text-muted-foreground">BUY steps</dt>
                <dd className="text-right font-medium">{result.transaction_distribution.buy}</dd>
                <dt className="text-muted-foreground">SELL steps</dt>
                <dd className="text-right font-medium">{result.transaction_distribution.sell}</dd>
                <dt className="text-muted-foreground">NO TRANSACTION</dt>
                <dd className="text-right font-medium">{result.transaction_distribution.no_transaction}</dd>
                <dt className="text-muted-foreground">Initial balance</dt>
                <dd className="text-right font-medium">{formatUsd(result.initial_balance)}</dd>
                <dt className="text-muted-foreground">Final balance</dt>
                <dd className="text-right font-medium">{formatUsd(result.final_balance)}</dd>
                <dt className="text-muted-foreground">PnL %</dt>
                <dd className="text-right font-medium">{formatPercent(result.pnl_pct)}</dd>
              </dl>
            ) : (
              <p data-testid="battle-empty" className="text-sm text-muted-foreground">
                No battle result yet. Run the best checkpoint to inspect the latest policy.
              </p>
            )}
          </CardContent>
        </Card>
      </section>

      <section className="mt-3">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-semibold">Recent Executed Trades</CardTitle>
          </CardHeader>
          <CardContent>
            {result?.executed_trades.length ? (
              <div className="space-y-3">
                {[...result.executed_trades].reverse().slice(0, 12).map((trade) => (
                  <div
                    className="rounded-md border border-border p-3 text-sm"
                    key={`${trade.timestamp}-${trade.action}-${trade.execution_price}`}
                  >
                    <div className="flex items-center justify-between gap-3">
                      <ActionBadge action={trade.action} />
                      <span className="text-xs text-muted-foreground">{formatTimestamp(trade.timestamp, timeMode)}</span>
                    </div>
                    <dl className="mt-2 grid grid-cols-2 gap-x-3 gap-y-1">
                      <dt className="text-muted-foreground">Price</dt>
                      <dd className="text-right font-medium">{formatUsd(trade.execution_price)}</dd>
                      <dt className="text-muted-foreground">Position</dt>
                      <dd className="text-right font-medium">
                        {trade.position_before.toFixed(2)} → {trade.position_after.toFixed(2)} · {(trade.size_percent * 100).toFixed(0)}%
                      </dd>
                      <dt className="text-muted-foreground">Balance after</dt>
                      <dd className="text-right font-medium">{formatUsd(trade.balance_after)}</dd>
                      <dt className="text-muted-foreground">Realized PnL</dt>
                      <dd className="text-right font-medium">{formatSignedUsd(trade.realized_pnl)}</dd>
                    </dl>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-sm text-muted-foreground">No executed trades captured yet.</p>
            )}
          </CardContent>
        </Card>
      </section>
    </main>
  )
}
