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
    <main className="dashboard">
      <header className="topbar">
        <h1>Runs</h1>
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
