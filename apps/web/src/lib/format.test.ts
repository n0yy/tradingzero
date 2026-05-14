import { describe, expect, it } from 'vitest'

import { formatPercent, formatSharpe, formatSignedUsd, formatUsd } from './format'

describe('formatUsd', () => {
  it('formats numeric value with 2 decimals and separators', () => {
    expect(formatUsd(123000)).toBe('$123,000.00')
  })

  it('returns em-dash placeholder for null', () => {
    expect(formatUsd(null)).toBe('—')
  })

  it('returns em-dash placeholder for undefined', () => {
    expect(formatUsd(undefined)).toBe('—')
  })
})

describe('formatPercent', () => {
  it('formats fractional value as percent with 2 decimals', () => {
    expect(formatPercent(0.5)).toBe('50.00%')
  })

  it('returns em-dash for null or undefined', () => {
    expect(formatPercent(null)).toBe('—')
    expect(formatPercent(undefined)).toBe('—')
  })
})

describe('formatSignedUsd', () => {
  it('prefixes positive values with +', () => {
    expect(formatSignedUsd(100)).toBe('+$100.00')
  })

  it('prefixes negative values with -', () => {
    expect(formatSignedUsd(-100)).toBe('-$100.00')
  })

  it('treats zero as positive', () => {
    expect(formatSignedUsd(0)).toBe('+$0.00')
  })

  it('returns em-dash for null', () => {
    expect(formatSignedUsd(null)).toBe('—')
  })
})

describe('formatSharpe', () => {
  it('formats sharpe with 4 decimals', () => {
    expect(formatSharpe(1.234567)).toBe('1.2346')
    expect(formatSharpe(-0.5)).toBe('-0.5000')
  })

  it('returns em-dash for null or undefined', () => {
    expect(formatSharpe(null)).toBe('—')
    expect(formatSharpe(undefined)).toBe('—')
  })
})
