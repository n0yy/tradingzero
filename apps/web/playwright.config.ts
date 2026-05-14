import { defineConfig } from '@playwright/test'
import { fileURLToPath } from 'node:url'
import path from 'node:path'

const configDir = path.dirname(fileURLToPath(import.meta.url))
const repoRoot = path.resolve(configDir, '..', '..')

export default defineConfig({
  testDir: './tests/e2e',
  timeout: 60_000,
  fullyParallel: false,
  reporter: [['list']],
  use: {
    baseURL: 'http://127.0.0.1:4174',
    screenshot: 'only-on-failure',
    trace: 'retain-on-failure',
    video: 'off',
  },
  webServer: [
    {
      command:
        "bash -lc 'TRADINGZERO_RUNNER_MODE=inmemory TRADINGZERO_DATABASE_URL=sqlite:////tmp/tradingzero-e2e-$PPID.db uv run python main.py --host 127.0.0.1 --port 8010'",
      cwd: repoRoot,
      url: 'http://127.0.0.1:8010/healthz',
      reuseExistingServer: false,
      timeout: 120_000,
    },
    {
      command: 'npm run dev -- --host 127.0.0.1 --port 4174',
      cwd: configDir,
      env: {
        ...process.env,
        TRADINGZERO_API_ORIGIN: 'http://127.0.0.1:8010',
      },
      url: 'http://127.0.0.1:4174',
      reuseExistingServer: false,
      timeout: 120_000,
    },
  ],
})
