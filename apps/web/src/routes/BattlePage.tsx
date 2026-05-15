import { useMutation, useQuery } from '@tanstack/react-query'

import { DashboardModeTabs } from '@/components/DashboardModeTabs'
import { ActionBadge } from '@/components/ActionBadge'
import { Button } from '@/components/ui/button'
import { fetchActiveConfig, runBestBattle } from '@/lib/api'
import { formatPercent, formatSignedUsd, formatUsd } from '@/lib/format'
import { useUIStore } from '@/store/ui'

function formatTimestamp(iso: string | null, mode: 'utc' | 'local'): string {
  if (!iso) return '—'
  const d = new Date(iso)
  return mode === 'utc' ? d.toISOString() : d.toLocaleString()
}

export default function BattlePage() {
  const timeMode = useUIStore((s) => s.timeMode)
  const toggleTimeMode = useUIStore((s) => s.toggleTimeMode)
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
    <main className="dashboard">
      <header className="topbar dashboard-topbar">
        <div className="dashboard-title-cluster">
          <div className="flex items-center gap-3">
            <h1>TradingZero Dashboard</h1>
            <span className="inline-flex rounded-full bg-secondary px-3 py-1 text-xs font-medium text-secondary-foreground">
              {battleMutation.isPending ? 'BATTLING' : result ? 'READY' : 'IDLE'}
            </span>
          </div>
          <p className="panel-subtle">Run the promoted `best.zip` once against the latest market slice.</p>
        </div>
        <DashboardModeTabs />
        <div className="dashboard-time-control">
          <Button onClick={toggleTimeMode} variant="outline" size="sm" type="button">
            Time: {timeMode.toUpperCase()}
          </Button>
        </div>
      </header>

      <section className="grid metrics battle-metrics">
        <article className="card">
          <span>Checkpoint</span>
          <strong data-testid="battle-checkpoint">best.zip</strong>
        </article>
        <article className="card">
          <span>Market</span>
          <strong data-testid="battle-market">
            {configQuery.data?.config?.data.symbol ?? '—'} {configQuery.data?.config?.data.timeframe ?? ''}
          </strong>
        </article>
        <article className="card">
          <span>Trade Win Rate</span>
          <strong data-testid="battle-win-rate">{formatPercent(result?.trade_win_rate)}</strong>
        </article>
        <article className="card">
          <span>Final Balance</span>
          <strong data-testid="battle-final-balance">{formatUsd(result?.final_balance)}</strong>
        </article>
        <article className="card">
          <span>PnL</span>
          <strong data-testid="battle-pnl">{formatSignedUsd(result?.pnl)}</strong>
        </article>
        <article className="card">
          <span>Total Trades</span>
          <strong data-testid="battle-total-trades">{result?.total_trades ?? '—'}</strong>
        </article>
      </section>

      <section className="grid history-grid">
        <article className="card panel">
          <h2>Battle Controls</h2>
          <p>Checkpoint path: {checkpointPath}</p>
          <p>
            Uses the active config for symbol, timeframe, env shape, and episode length, then runs one deterministic
            inference pass.
          </p>
          <div className="controls-row">
            <Button
              data-testid="run-battle"
              type="button"
              onClick={() => battleMutation.mutate()}
              disabled={battleMutation.isPending}
            >
              {battleMutation.isPending ? 'Running Battle...' : 'Run Best Agent'}
            </Button>
          </div>
          {battleMutation.isError && (
            <p className="loss" data-testid="battle-error">
              {battleError ?? 'Battle failed. Check that `best.zip` exists and matches the active environment.'}
            </p>
          )}
          {result && (
            <p className="text-sm text-muted-foreground" data-testid="battle-summary-line">
              {result.total_steps} steps · {result.winning_trades}/{realizedExitCount} winning realized exits.
            </p>
          )}
        </article>

        <article className="card panel">
          <h2>Outcome Summary</h2>
          {result ? (
            <div className="grid gap-3">
              <div className="run-row">
                <p>Winning exits: {result.winning_trades}</p>
                <p>Losing exits: {result.losing_trades}</p>
                <p>Flat exits: {result.flat_trades}</p>
              </div>
              <div className="run-row">
                <p>BUY steps: {result.transaction_distribution.buy}</p>
                <p>SELL steps: {result.transaction_distribution.sell}</p>
                <p>NO TRANSACTION: {result.transaction_distribution.no_transaction}</p>
              </div>
              <div className="run-row">
                <p>Initial balance: {formatUsd(result.initial_balance)}</p>
                <p>Final balance: {formatUsd(result.final_balance)}</p>
                <p>PnL %: {formatPercent(result.pnl_pct)}</p>
              </div>
            </div>
          ) : (
            <p data-testid="battle-empty">No battle result yet. Run the best checkpoint to inspect the latest policy.</p>
          )}
        </article>
      </section>

      <section className="grid">
        <article className="card panel">
          <h2>Recent Executed Trades</h2>
          {result?.executed_trades.length ? (
            <div className="run-list">
              {[...result.executed_trades].reverse().slice(0, 12).map((trade) => (
                <div className="run-row" key={`${trade.timestamp}-${trade.action}-${trade.execution_price}`}>
                  <div className="flex items-center justify-between gap-3">
                    <ActionBadge action={trade.action} />
                    <span className="text-xs text-muted-foreground">{formatTimestamp(trade.timestamp, timeMode)}</span>
                  </div>
                  <p>Price: {formatUsd(trade.execution_price)}</p>
                  <p>
                    Position: {trade.position_before.toFixed(2)} → {trade.position_after.toFixed(2)} · Size{' '}
                    {(trade.size_percent * 100).toFixed(0)}%
                  </p>
                  <p>Balance after: {formatUsd(trade.balance_after)}</p>
                  <p>Realized PnL: {formatSignedUsd(trade.realized_pnl)}</p>
                </div>
              ))}
            </div>
          ) : (
            <p>No executed trades captured yet.</p>
          )}
        </article>
      </section>
    </main>
  )
}
