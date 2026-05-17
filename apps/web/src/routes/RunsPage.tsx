import { useQuery } from '@tanstack/react-query'

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { fetchRuns } from '@/lib/api'
import { useUIStore } from '../store/ui'

function formatTimestamp(iso: string | null, mode: 'utc' | 'local'): string {
  if (!iso) return '-'
  const d = new Date(iso)
  return mode === 'utc' ? d.toISOString() : d.toLocaleString()
}

function stateColor(state: string) {
  if (state === 'done') return 'text-green-500'
  if (state === 'error') return 'text-destructive'
  if (state === 'running') return 'text-(--gain)'
  return 'text-muted-foreground'
}

export default function RunsPage() {
  const timeMode = useUIStore((s) => s.timeMode)
  const runsQuery = useQuery({
    queryKey: ['runs-history'],
    queryFn: fetchRuns,
    refetchInterval: 4000,
  })

  return (
    <main className="mx-auto w-full max-w-none px-4 py-4 md:px-6">
      <header className="mb-4">
        <h1 className="font-display text-2xl tracking-wide text-foreground">Runs</h1>
      </header>
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-semibold">Run History</CardTitle>
        </CardHeader>
        <CardContent>
          {runsQuery.data?.runs?.length ? (
            <div className="space-y-2">
              {runsQuery.data.runs.map((run) => (
                <div
                  className="rounded-md border border-border p-3 text-sm"
                  key={run.run_id}
                >
                  <div className="flex items-center justify-between gap-2">
                    <span className="font-mono text-xs text-foreground">{run.run_id}</span>
                    <span className={`text-xs font-semibold uppercase ${stateColor(run.state)}`}>{run.state}</span>
                  </div>
                  <p className="mt-1 text-xs text-muted-foreground">{formatTimestamp(run.started_at, timeMode)}</p>
                  {run.evaluation_summary && (
                    <dl className="mt-2 grid grid-cols-2 gap-x-3 gap-y-0.5 text-xs">
                      <dt className="text-muted-foreground">Promotion</dt>
                      <dd className="text-right font-medium">
                        {run.evaluation_summary.latest_promotion_outcome === 'promoted' ? 'Promoted' : 'Not promoted'}
                      </dd>
                      <dt className="text-muted-foreground">Best Eval Sharpe</dt>
                      <dd className="text-right font-medium">
                        {run.evaluation_summary.best_evaluation_sharpe.toFixed(4)}
                      </dd>
                    </dl>
                  )}
                </div>
              ))}
            </div>
          ) : (
            <p className="text-sm text-muted-foreground">Belum ada history run.</p>
          )}
        </CardContent>
      </Card>
    </main>
  )
}
