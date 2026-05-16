import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'

describe('theme foundation', () => {
  const indexCss = readFileSync(resolve(process.cwd(), 'src/index.css'), 'utf-8')

  it('does not declare a dark mode variant', () => {
    expect(indexCss).not.toMatch(/@custom-variant\s+dark/i)
    expect(indexCss).not.toMatch(/\.dark\s*\{/)
  })

  it('imports tailwindcss', () => {
    expect(indexCss).toMatch(/@import\s+['"]tailwindcss['"]/i)
  })

  it('uses a light background', () => {
    expect(indexCss).toMatch(/--background:\s*#ffffff/)
  })

  it('declares the gain and loss accent tokens', () => {
    expect(indexCss).toMatch(/--gain:/)
    expect(indexCss).toMatch(/--loss:/)
  })

  it('declares neumorphism shadow tokens', () => {
    expect(indexCss).toMatch(/--neu-shadow:/)
    expect(indexCss).toMatch(/--neu-shadow-inset:/)
  })
})
