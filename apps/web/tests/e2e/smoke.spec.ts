import { expect, test } from '@playwright/test'
import { mkdirSync, writeFileSync } from 'node:fs'
import { join } from 'node:path'

const consoleBuffer = new Map<string, string[]>()

test.beforeEach(async ({ page }, testInfo) => {
  const logs: string[] = []
  consoleBuffer.set(testInfo.testId, logs)
  page.on('console', (msg) => logs.push(`[${msg.type()}] ${msg.text()}`))
})

test.afterEach(async ({}, testInfo) => {
  if (testInfo.status === testInfo.expectedStatus) return
  const logs = consoleBuffer.get(testInfo.testId) || []
  const outDir = join(testInfo.outputDir, 'console-artifacts')
  mkdirSync(outDir, { recursive: true })
  writeFileSync(join(outDir, 'browser-console.log'), logs.join('\n'), 'utf-8')
})

test('live view golden path @smoke', async ({ page }) => {
  await page.goto('/')

  await expect(page.getByText('TradingZero Dashboard')).toBeVisible()
  await expect(page.getByRole('navigation', { name: /primary/i })).toBeVisible()
  await expect(page.getByTestId('live-view-state')).toBeVisible()
  await expect(page.getByTestId('last-action-empty')).toBeVisible()
  await expect(page.getByTestId('chart-state-helper')).toBeVisible()

  await expect(page.getByTestId('start-run')).toBeVisible()
  await page.getByTestId('start-run').click()
  await expect(page.getByTestId('live-view-state')).toHaveText(/waiting|running/i, { timeout: 20_000 })
  await expect(page.getByTestId('price-chart')).toBeVisible({ timeout: 20_000 })
  await expect(page.getByTestId('last-action-direction')).toBeVisible({ timeout: 20_000 })
  await expect(page.getByTestId('kpi-balance')).not.toHaveText('—', { timeout: 20_000 })
  await expect(page.getByTestId('kpi-pnl')).not.toHaveText('—', { timeout: 20_000 })

  const firstBalance = (await page.getByTestId('kpi-balance').textContent()) ?? ''
  await expect
    .poll(async () => (await page.getByTestId('kpi-balance').textContent()) ?? '', { timeout: 10_000 })
    .not.toBe(firstBalance)

  await page.getByTestId('stop-run').click()
  await expect(page.getByTestId('live-view-state')).toHaveText(/stopping|done|idle/i, { timeout: 20_000 })
})

test('routes mount Live View, Config, Runs, Errors @smoke', async ({ page }) => {
  await page.goto('/config')
  await expect(page.getByRole('button', { name: /save revision/i })).toBeVisible()
  await expect(page.getByRole('group', { name: /^data$/i })).toBeVisible()

  await page.goto('/runs')
  await expect(page.getByRole('heading', { name: /run history/i })).toBeVisible()

  await page.goto('/errors')
  await expect(page.getByRole('heading', { name: /error explorer/i })).toBeVisible()

  await page.goto('/')
  await expect(page.getByText('TradingZero Dashboard')).toBeVisible()
})

test('debug capture page health @debug', async ({ page }) => {
  await page.goto('/')
  await expect(page.getByText('TradingZero Dashboard')).toBeVisible()
})
