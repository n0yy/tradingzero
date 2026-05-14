import { Badge } from '@/components/ui/badge'
import { cn } from '@/lib/utils'
import { liveViewStateLabel, type LiveViewState } from '@/lib/liveViewState'

type Variant = 'default' | 'secondary' | 'destructive' | 'outline'

const variantByKind: Record<LiveViewState['kind'], Variant> = {
  disconnected: 'destructive',
  idle: 'outline',
  waiting: 'secondary',
  running: 'default',
  stopping: 'secondary',
  done: 'outline',
  error: 'destructive',
}

export function LiveViewStateBadge({
  state,
  className,
  testId = 'live-view-state',
}: {
  state: LiveViewState
  className?: string
  testId?: string
}) {
  return (
    <Badge
      data-testid={testId}
      variant={variantByKind[state.kind]}
      className={cn('uppercase tracking-wide', className)}
    >
      {liveViewStateLabel(state.kind)}
    </Badge>
  )
}

const helperByKind: Record<LiveViewState['kind'], string> = {
  disconnected: 'Live Stream disconnected — reconnecting…',
  idle: 'Idle — start a Run to begin live monitoring.',
  waiting: 'Waiting for the first training event from the active Run.',
  running: '',
  stopping: 'Stopping the active Run — finishing current Generation.',
  done: 'Run completed. Inspect history or start a new Run.',
  error: '',
}

export function ChartStateHelper({ state }: { state: LiveViewState }) {
  if (state.kind === 'running') return null
  const text =
    state.kind === 'error'
      ? `Run errored${state.error ? `: ${state.error}` : ''}.`
      : helperByKind[state.kind]

  return (
    <div
      data-testid="chart-state-helper"
      className={cn(
        'flex h-full min-h-50 flex-col items-center justify-center gap-2 rounded-xl border border-dashed border-border/60 bg-card/40 p-6 text-center',
      )}
    >
      <LiveViewStateBadge state={state} testId="chart-state-badge" />
      <p className="max-w-md text-sm text-muted-foreground">{text}</p>
    </div>
  )
}
