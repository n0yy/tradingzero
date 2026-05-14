import { useQuery } from '@tanstack/react-query'

import { fetchRunErrors, fetchRunStatus, fetchRuns } from '@/lib/api'
import { useUIStore } from '../store/ui'

function formatTimestamp(iso: string | null, mode: 'utc' | 'local'): string {
  if (!iso) return '-'
  const d = new Date(iso)
  return mode === 'utc' ? d.toISOString() : d.toLocaleString()
}

export default function ErrorsPage() {
  const timeMode = useUIStore((s) => s.timeMode)
  const statusQuery = useQuery({
    queryKey: ['run-status'],
    queryFn: fetchRunStatus,
    refetchInterval: 3000,
  })
  const runsQuery = useQuery({
    queryKey: ['runs-history'],
    queryFn: fetchRuns,
    refetchInterval: 4000,
  })
  const selectedRunId = statusQuery.data?.run_id ?? runsQuery.data?.runs?.[0]?.run_id
  const errorsQuery = useQuery({
    queryKey: ['run-errors', selectedRunId],
    queryFn: () => fetchRunErrors(selectedRunId as string),
    enabled: Boolean(selectedRunId),
    refetchInterval: 4000,
  })

  return (
    <main className="dashboard">
      <header className="topbar">
        <h1>Errors</h1>
      </header>
      <section className="grid history-grid">
        <article className="card panel">
          <h2>Error Explorer</h2>
          {errorsQuery.data?.errors?.length ? (
            <div className="run-list">
              {errorsQuery.data.errors.map((err) => (
                <div className="run-row run-error" key={`${err.created_at}-${err.code}`}>
                  <p>{err.code}</p>
                  <p>{err.message}</p>
                  <p>{formatTimestamp(err.created_at, timeMode)}</p>
                </div>
              ))}
            </div>
          ) : (
            <p>Tidak ada error untuk run terpilih.</p>
          )}
        </article>
      </section>
    </main>
  )
}
