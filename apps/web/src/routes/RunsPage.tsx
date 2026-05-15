import { useQuery } from '@tanstack/react-query'

import { fetchRuns } from '@/lib/api'
import { useUIStore } from '../store/ui'

function formatTimestamp(iso: string | null, mode: 'utc' | 'local'): string {
  if (!iso) return '-'
  const d = new Date(iso)
  return mode === 'utc' ? d.toISOString() : d.toLocaleString()
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
      <section className="grid history-grid">
        <article className="card panel">
          <h2>Run History</h2>
          {runsQuery.data?.runs?.length ? (
            <div className="run-list">
              {runsQuery.data.runs.map((run) => (
                <div className={`run-row ${run.state === 'error' ? 'run-error' : ''}`} key={run.run_id}>
                  <p>{run.run_id}</p>
                  <p>{run.state.toUpperCase()}</p>
                  <p>{formatTimestamp(run.started_at, timeMode)}</p>
                  {run.evaluation_summary ? (
                    <div className="mt-2 grid gap-1 text-xs text-muted-foreground">
                      <p>
                        Promotion: <span className="font-medium text-foreground">{run.evaluation_summary.latest_promotion_outcome === 'promoted' ? 'Promoted' : 'Not promoted'}</span>
                      </p>
                      <p>
                        Best Eval Sharpe:{' '}
                        <span className="font-medium text-foreground">
                          {run.evaluation_summary.best_evaluation_sharpe.toFixed(4)}
                        </span>
                      </p>
                    </div>
                  ) : null}
                </div>
              ))}
            </div>
          ) : (
            <p>Belum ada history run.</p>
          )}
        </article>
      </section>
    </main>
  )
}
