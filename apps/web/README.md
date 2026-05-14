# TradingZero Web App

React + Vite dashboard untuk observability dan kontrol lifecycle training.

## Local Run

```bash
cd apps/web
npm install
npm run dev
npm run test
npm run build
```

Dev server berjalan di `http://127.0.0.1:4173` dan proxy ke backend `http://127.0.0.1:8000` untuk endpoint `/runs`, `/config`, `/healthz`, dan websocket `/ws`.

## E2E Harness (Playwright)

Tag test:

- `@smoke`: jalur cepat wajib CI (`open -> start -> stream connected -> stop`)
- `@debug`: jalur tambahan untuk investigasi lokal

Command:

```bash
npm run e2e:smoke
npm run e2e:debug
```

Artifact saat gagal:

- screenshot (`only-on-failure`)
- trace (`retain-on-failure`)
- browser console log (`browser-console.log` di output test)
