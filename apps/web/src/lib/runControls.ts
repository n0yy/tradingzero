import type { LiveViewStateKind } from './liveViewState'

export type RunControlVisibility = {
  start: boolean
  stop: boolean
  retry: boolean
}

export function runControlVisibility(kind: LiveViewStateKind): RunControlVisibility {
  switch (kind) {
    case 'idle':
    case 'disconnected':
      return { start: true, stop: false, retry: false }
    case 'waiting':
    case 'running':
    case 'stopping':
      return { start: false, stop: true, retry: false }
    case 'done':
      return { start: true, stop: false, retry: true }
    case 'error':
      return { start: true, stop: false, retry: true }
  }
}
