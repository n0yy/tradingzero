import { useMemo } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import PriceChart from '../components/PriceChart'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { ActionDistributionPanel } from '@/components/ActionDistributionPanel'
import { ChartStateHelper, LiveViewStateBadge } from '@/components/LiveViewStateBanner'
import { KpiStrip } from '@/components/KpiStrip'
import { LastActionPanel } from '@/components/LastActionPanel'
import { PromotionCheckPanel } from '@/components/PromotionCheckPanel'
import { fetchRunStatus, retryRun, startRun, stopRun } from '@/lib/api'
import { deriveLiveViewState } from '@/lib/liveViewState'
import { runControlVisibility } from '@/lib/runControls'
import { useTrainingStream } from '../hooks/useTrainingStream'
import { useUIStore } from '../store/ui'

function formatTimestamp(iso: string | null, mode: 'utc' | 'local'): string {
  if (!iso) return '-'
  const d = new Date(iso)
  return mode === 'utc' ? d.toISOString() : d.toLocaleString()
}

export default function LiveView() {
  const qc = useQueryClient()
  const statusQuery = useQuery({
    queryKey: ['run-status'],
    queryFn: fetchRunStatus,
    refetchInterval: 3000,
  })
  const streamState = useTrainingStream(statusQuery.data?.run_id ?? null)
  const stream = streamState.event
  const stepBatch = streamState.stepBatch
  const priceBuffer = streamState.priceBuffer
  const timeMode = useUIStore((s) => s.timeMode)
  const retryMutation = useMutation({
    mutationFn: retryRun,
    onSuccess: async () => {
      await qc.invalidateQueries({ queryKey: ['run-status'] })
      await qc.invalidateQueries({ queryKey: ['runs-history'] })
    },
  })
  const startMutation = useMutation({
    mutationFn: startRun,
    onSuccess: async () => {
      await qc.invalidateQueries({ queryKey: ['run-status'] })
      await qc.invalidateQueries({ queryKey: ['runs-history'] })
    },
  })
  const stopMutation = useMutation({
    mutationFn: stopRun,
    onSuccess: async () => {
      await qc.invalidateQueries({ queryKey: ['run-status'] })
      await qc.invalidateQueries({ queryKey: ['runs-history'] })
    },
  })

  const liveState = useMemo(
    () =>
      deriveLiveViewState({
        runState: statusQuery.data?.state,
        streamConnected: streamState.connected,
        hasEvent: stream !== null || stepBatch !== null,
        runId: statusQuery.data?.run_id ?? null,
        error: statusQuery.data?.error ?? null,
      }),
    [statusQuery.data?.state, statusQuery.data?.run_id, statusQuery.data?.error, streamState.connected, stream, stepBatch],
  )

  const controls = runControlVisibility(liveState.kind)

  return (
    <main className="mx-auto w-full max-w-none px-4 py-4 md:px-6">
      <header className="mb-4 grid gap-3">
        <div className="min-w-0">
          <div className="flex items-center gap-3">
            <h1 className="font-display text-2xl tracking-wide text-foreground">TradingZero Dashboard</h1>
            <LiveViewStateBadge state={liveState} />
          </div>
          <p className="text-sm text-muted-foreground">Training stream, checkpoints, and live portfolio telemetry.</p>
        </div>
      </header>

      <KpiStrip event={stream} stepBatch={stepBatch} />

      <section className="mt-3 grid gap-3 xl:grid-cols-[minmax(0,7fr)_minmax(320px,3fr)]">
        <div>
          {liveState.kind === 'running' ? (
            <div className="rounded-xl border border-border/60 bg-card p-2">
              <PriceChart event={stream} priceBuffer={priceBuffer} height={460} />
            </div>
          ) : (
            <ChartStateHelper state={liveState} />
          )}
        </div>
        <PromotionCheckPanel event={stream} />
      </section>

      <section className="mt-3 grid gap-3 xl:grid-cols-3">
        <Card>
          <CardHeader>
            <CardTitle className="font-semibold">Run Status</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2 text-sm">
            <p className="text-muted-foreground">Run ID: <span className="font-mono text-foreground">{statusQuery.data?.run_id ?? '-'}</span></p>
            <p className="text-muted-foreground">Started: <span className="text-foreground">{formatTimestamp(statusQuery.data?.started_at ?? null, timeMode)}</span></p>
            {liveState.kind === 'error' && liveState.error && (
              <p className="text-sm text-destructive">Error: {liveState.error}</p>
            )}
            {(controls.start || controls.stop) && (
              <div className="flex gap-2 pt-1">
                {controls.start && (
                  <Button
                    variant="outline"
                    size="sm"
                    data-testid="start-run"
                    type="button"
                    onClick={() => startMutation.mutate()}
                    disabled={startMutation.isPending}
                  >
                    {startMutation.isPending ? 'Starting...' : 'Start Run'}
                  </Button>
                )}
                {controls.stop && (
                  <Button
                    variant="outline"
                    size="sm"
                    data-testid="stop-run"
                    type="button"
                    onClick={() => stopMutation.mutate()}
                    disabled={stopMutation.isPending || liveState.kind === 'stopping'}
                  >
                    {stopMutation.isPending || liveState.kind === 'stopping' ? 'Stopping...' : 'Stop Run'}
                  </Button>
                )}
              </div>
            )}
            {controls.retry && (
              <Button
                variant="outline"
                size="sm"
                className="w-full"
                data-testid="retry-run"
                type="button"
                onClick={() => retryMutation.mutate()}
                disabled={retryMutation.isPending}
              >
                {retryMutation.isPending ? 'Retrying...' : 'Retry Latest Checkpoint'}
              </Button>
            )}
            {retryMutation.isError && (
              <p className="text-sm text-destructive">Retry blocked or failed.</p>
            )}
          </CardContent>
        </Card>

        <LastActionPanel event={stream} />
        <ActionDistributionPanel event={stream} />
      </section>
    </main>
  )
}
