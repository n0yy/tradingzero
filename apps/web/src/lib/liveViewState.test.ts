import { describe, expect, it } from 'vitest'

import { deriveLiveViewState } from './liveViewState'

describe('deriveLiveViewState', () => {
  it('returns disconnected when stream is not connected, regardless of run state', () => {
    expect(deriveLiveViewState({ runState: 'idle', streamConnected: false, hasEvent: false }))
      .toEqual({ kind: 'disconnected' })
    expect(deriveLiveViewState({ runState: 'running', streamConnected: false, hasEvent: true, runId: 'r1' }))
      .toEqual({ kind: 'disconnected' })
  })

  it('returns idle when run is idle and stream is connected', () => {
    expect(deriveLiveViewState({ runState: 'idle', streamConnected: true, hasEvent: false }))
      .toEqual({ kind: 'idle' })
  })

  it('treats unknown or missing run state as idle when stream is connected', () => {
    expect(deriveLiveViewState({ runState: undefined, streamConnected: true, hasEvent: false }))
      .toEqual({ kind: 'idle' })
  })

  it('returns waiting when run is running but no event has arrived yet', () => {
    expect(
      deriveLiveViewState({ runState: 'running', streamConnected: true, hasEvent: false, runId: 'r1' }),
    ).toEqual({ kind: 'waiting', runId: 'r1' })
  })

  it('returns running when run is running and an event has arrived', () => {
    expect(
      deriveLiveViewState({ runState: 'running', streamConnected: true, hasEvent: true, runId: 'r1' }),
    ).toEqual({ kind: 'running', runId: 'r1' })
  })

  it('returns stopping when run is stopping', () => {
    expect(
      deriveLiveViewState({ runState: 'stopping', streamConnected: true, hasEvent: true, runId: 'r1' }),
    ).toEqual({ kind: 'stopping', runId: 'r1' })
  })

  it('returns done when run is done', () => {
    expect(
      deriveLiveViewState({ runState: 'done', streamConnected: true, hasEvent: true, runId: 'r1' }),
    ).toEqual({ kind: 'done', runId: 'r1' })
  })

  it('returns error with the error string when run is in error state', () => {
    expect(
      deriveLiveViewState({
        runState: 'error',
        streamConnected: true,
        hasEvent: false,
        runId: 'r1',
        error: 'OOM',
      }),
    ).toEqual({ kind: 'error', runId: 'r1', error: 'OOM' })
  })
})
