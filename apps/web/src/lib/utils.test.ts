import { describe, expect, it } from 'vitest'

import { cn } from './utils'

describe('cn', () => {
  it('joins class names with spaces', () => {
    expect(cn('a', 'b')).toBe('a b')
  })

  it('drops falsy values', () => {
    expect(cn('a', false && 'b', null, undefined, 'c')).toBe('a c')
  })

  it('resolves tailwind conflicts so the later wins', () => {
    expect(cn('p-2', 'p-4')).toBe('p-4')
    expect(cn('text-sm', 'text-lg')).toBe('text-lg')
  })

  it('accepts conditional class objects', () => {
    expect(cn({ active: true, hidden: false }, 'extra')).toBe('active extra')
  })
})
