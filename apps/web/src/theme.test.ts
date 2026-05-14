import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'

describe('theme foundation', () => {
  const indexCss = readFileSync(resolve(process.cwd(), 'src/index.css'), 'utf-8')

  it('does not declare a prefers-color-scheme: light override', () => {
    expect(indexCss).not.toMatch(/@media\s*\(\s*prefers-color-scheme:\s*light\s*\)/i)
  })

  it('imports tailwindcss', () => {
    expect(indexCss).toMatch(/@import\s+['"]tailwindcss['"]/i)
  })

  it('exposes a custom dark variant gated on the .dark class', () => {
    expect(indexCss).toMatch(/@custom-variant\s+dark[^;]*\.dark/i)
  })

  it('declares the gain and loss accent tokens', () => {
    expect(indexCss).toMatch(/--gain:/)
    expect(indexCss).toMatch(/--loss:/)
  })
})
