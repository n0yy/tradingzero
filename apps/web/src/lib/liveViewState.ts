export type RunState = 'idle' | 'running' | 'stopping' | 'done' | 'error' | string

export type LiveViewState =
  | { kind: 'disconnected' }
  | { kind: 'idle' }
  | { kind: 'waiting'; runId: string | null }
  | { kind: 'running'; runId: string | null }
  | { kind: 'stopping'; runId: string | null }
  | { kind: 'done'; runId: string | null }
  | { kind: 'error'; runId: string | null; error: string | null }

export type DeriveInput = {
  runState: RunState | undefined
  streamConnected: boolean
  hasEvent: boolean
  runId?: string | null
  error?: string | null
}

export function deriveLiveViewState(input: DeriveInput): LiveViewState {
  const { runState, streamConnected, hasEvent, runId = null, error = null } = input

  if (!streamConnected) return { kind: 'disconnected' }

  switch (runState) {
    case 'error':
      return { kind: 'error', runId, error }
    case 'running':
      return hasEvent ? { kind: 'running', runId } : { kind: 'waiting', runId }
    case 'stopping':
      return { kind: 'stopping', runId }
    case 'done':
      return { kind: 'done', runId }
    case 'idle':
    default:
      return { kind: 'idle' }
  }
}

export type LiveViewStateKind = LiveViewState['kind']

export function liveViewStateLabel(kind: LiveViewStateKind): string {
  switch (kind) {
    case 'disconnected':
      return 'Disconnected'
    case 'idle':
      return 'Idle'
    case 'waiting':
      return 'Waiting'
    case 'running':
      return 'Running'
    case 'stopping':
      return 'Stopping'
    case 'done':
      return 'Done'
    case 'error':
      return 'Error'
  }
}
