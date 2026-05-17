import { useQuery } from '@tanstack/react-query'

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
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
    <main className="mx-auto w-full max-w-none px-4 py-4 md:px-6">
      <header className="mb-4">
        <h1 className="font-display text-2xl tracking-wide text-foreground">Errors</h1>
      </header>
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-semibold">Error Explorer</CardTitle>
        </CardHeader>
        <CardContent>
          {errorsQuery.data?.errors?.length ? (
            <div className="space-y-2">
              {errorsQuery.data.errors.map((err) => (
                <div
                  className="rounded-md border border-destructive/30 bg-destructive/5 p-3 text-sm"
                  key={`${err.created_at}-${err.code}`}
                >
                  <div className="flex items-center justify-between gap-2">
                    <span className="font-mono text-xs font-semibold text-destructive">{err.code}</span>
                    <span className="text-xs text-muted-foreground">{formatTimestamp(err.created_at, timeMode)}</span>
                  </div>
                  <p className="mt-1 text-sm text-foreground">{err.message}</p>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-sm text-muted-foreground">Tidak ada error untuk run terpilih.</p>
          )}
        </CardContent>
      </Card>
    </main>
  )
}
