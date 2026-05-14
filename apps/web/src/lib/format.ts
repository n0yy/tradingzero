const PLACEHOLDER = '—'

type MaybeNumber = number | null | undefined

function isPresent(value: MaybeNumber): value is number {
  return value !== null && value !== undefined && Number.isFinite(value)
}

export function formatUsd(value: MaybeNumber): string {
  if (!isPresent(value)) return PLACEHOLDER
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(value)
}

export function formatPercent(value: MaybeNumber): string {
  if (!isPresent(value)) return PLACEHOLDER
  return `${(value * 100).toFixed(2)}%`
}

export function formatSignedUsd(value: MaybeNumber): string {
  if (!isPresent(value)) return PLACEHOLDER
  const abs = formatUsd(Math.abs(value))
  return value >= 0 ? `+${abs}` : `-${abs}`
}

export function formatSharpe(value: MaybeNumber): string {
  if (!isPresent(value)) return PLACEHOLDER
  return value.toFixed(4)
}
