import { describe, expect, it } from 'vitest'

import { runControlVisibility } from './runControls'

describe('runControlVisibility', () => {
  it('shows Start at idle', () => {
    expect(runControlVisibility('idle')).toEqual({ start: true, stop: false, retry: false })
  })

  it('shows Start at disconnected so the user can recover', () => {
    expect(runControlVisibility('disconnected')).toEqual({ start: true, stop: false, retry: false })
  })

  it('shows Stop at running and waiting', () => {
    expect(runControlVisibility('running')).toEqual({ start: false, stop: true, retry: false })
    expect(runControlVisibility('waiting')).toEqual({ start: false, stop: true, retry: false })
  })

  it('shows Stop while stopping for clarity', () => {
    expect(runControlVisibility('stopping')).toEqual({ start: false, stop: true, retry: false })
  })

  it('shows Start and Retry at done', () => {
    expect(runControlVisibility('done')).toEqual({ start: true, stop: false, retry: true })
  })

  it('shows Start and Retry at error', () => {
    expect(runControlVisibility('error')).toEqual({ start: true, stop: false, retry: true })
  })
})
