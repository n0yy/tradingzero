# TradingZero

TradingZero adalah sistem trading berbasis Reinforcement Learning yang belajar strategi crypto murni dari self-play — tanpa indikator teknikal buatan tangan. Agent berevolusi dengan cara mengalahkan versi dirinya sendiri, menghasilkan strategi adaptif yang semakin tajam dari generasi ke generasi.

Terinspirasi dari AlphaZero.

---

## Abstrak

### Apa yang dilakukan proyek ini?

TradingZero melatih sebuah agent RL untuk berdagang aset kripto secara otomatis. Agent tidak diberi aturan trading apapun — ia hanya melihat data harga mentah (candle OHLCV) dan belajar sendiri kapan harus beli, jual, atau tahan posisi, dengan tujuan memaksimalkan Sharpe ratio (return yang disesuaikan dengan risiko).

Proses training berjalan dalam **generasi**: setiap generasi, agent berlatih lalu dievaluasi. Jika performanya meningkat signifikan dibanding versi terbaik sebelumnya, ia dipromosikan dan disimpan sebagai checkpoint baru. Siklus ini terus berulang — agent terus bersaing melawan dirinya sendiri, seperti AlphaZero di catur.

### Apa yang dilakukan agent?

Agent mengamati **60 candle terakhir** (window 60 × 7 channel) yang berisi:
- Data harga: open, high, low, close, volume (dinormalisasi)
- Posisi saat ini: fraksi modal yang sedang diinvestasikan [0.0–1.0]
- Unrealized PnL: keuntungan/kerugian yang belum direalisasi (dinormalisasi)

Dari observasi itu, agent memilih **dua keputusan sekaligus**:
1. **Arah** — Hold, Buy, atau Sell
2. **Ukuran** — 25%, 50%, 75%, atau 100% dari posisi

Contoh: agent bisa memilih "Buy 25%" untuk masuk secara bertahap, atau "Sell 100%" untuk keluar penuh. Posisi bersifat aditif dan di-clamp ke [0.0, 1.0], sehingga agent bisa membangun posisi secara parsial.

Reward dihitung dari **rolling Sharpe ratio** atas return episode, ditambah sinyal harga langsung kecil agar agent mendapat gradien bahkan saat holding. Setiap transaksi dikenai biaya proporsional terhadap perubahan posisi aktual.

---

## Status

Active development. Latest run (2026-05-14):
- Best Sharpe: **2.1152** @ generation 8
- Initial balance: $10,000 | tracked via real-time PnL dashboard
- Training on BTC/USDT 15m candles (Binance)

---

## How It Works

1. **Data Layer** — mengambil candle OHLCV dari exchange (Binance, OKX, Bybit) via CCXT, dinormalisasi menjadi rolling window.
2. **Environment** — custom Gymnasium env. Agent mengamati 60 candle × 7 channel dan memilih arah + ukuran posisi. Reward adalah Sharpe ratio + sinyal harga langsung, dikurangi transaction cost.
3. **Self-Play Training** — PPO (Stable-Baselines3) berlatih lintas generasi. Jika Sharpe agent saat ini melampaui best Sharpe sebesar `promote_threshold`, agent dipromosikan dan disimpan sebagai `best.zip`.
4. **Web Platform** — backend FastAPI + frontend React (Vite) sebagai pondasi monitoring dan kontrol training berbasis browser.

---

## Architecture

```
main.py                 ← web backend entry point (Uvicorn launcher)
├── backend/app.py      ← FastAPI app + health endpoint
├── logger.py           ← shared logger (Loguru)
├── data/fetcher.py     ← CCXT data pipeline + normalisasi
├── env/crypto_env.py   ← Gymnasium environment
│     observation: Box(60, 7)  — OHLCV + position + unrealized_pnl
│     action:      MultiDiscrete([3, 4])  — direction × size
├── agent/trainer.py    ← PPO self-play loop
│     _evaluate()       — transaction metrics, price_series, Sharpe snapshot
│     _notify()         → queue / streaming sink (next phase)
├── apps/web/           ← React + Vite + TypeScript frontend skeleton
└── run_best.py         ← inference runner + compat check
```

---

## Tech Stack

| Category | Libraries |
|----------|-----------|
| RL / ML | PyTorch, Stable-Baselines3, Gymnasium |
| Data | CCXT, Pandas, NumPy |
| Backend API | FastAPI, Uvicorn, Pydantic |
| Frontend | React, Vite, TypeScript |
| Testing | Pytest, pytest-cov, pytest-mock, Hypothesis |
| Tooling | Weights & Biases, python-dotenv, Loguru |

---

## Getting Started

```bash
# Install dependencies (requires uv)
uv sync

# Configure
# Edit config.yaml — set exchange, symbol, hyperparameters

# Run web backend
uv run python main.py

# Run frontend
cd apps/web && npm install
cd apps/web && npm run dev

# Run backend + frontend together
make dev

# Run TUI (secondary interface)
make tui

# Run best checkpoint (inference)
uv run python run_best.py
uv run python run_best.py --checkpoint agent/checkpoints/gen_0200.zip
```

---

## Configuration

All settings live in `config.yaml`:

| Section | Key settings |
|---------|-------------|
| `data` | exchange, symbol, timeframe, window_size |
| `env` | initial_balance, transaction_cost, episode_length |
| `agent` | learning_rate, n_steps, batch_size, total_episodes, promote_threshold |
| `self_play` | checkpoint_interval, checkpoint_dir |
| `logging` | wandb, project_name |

---

## Web Platform (Current Slice)

Bootstrap web stack fase awal:

- Backend FastAPI jalan di `http://localhost:8000`
- Health check: `GET /healthz` mengembalikan `{"status":"ok"}`
- Frontend Vite jalan di `http://localhost:5173`
- Mode concurrent lokal: `make dev`
- Persistence lokal: SQLite `data/tradingzero.db` (migrate via `make db-migrate`)
- Retention otomatis: prune run/event/error lebih lama dari 90 hari saat `POST /runs/start`
- Web UI adalah interface utama untuk start/stop/retry + observability.
- TUI tetap dipertahankan sebagai interface sekunder untuk workflow terminal-first (`apps/tui`).

---

## Testing

```bash
uv run pytest tests/unit/ -v
uv run pytest tests/integration/ -v
cd apps/web && npm test
cd apps/web && npm run e2e:smoke
```

Test layers:
- **Unit** (`tests/unit/`) — isolated tests untuk web entrypoint, health endpoint, env, data pipeline, trainer, run_best
- **Property-based** — Hypothesis tests untuk edge case environment (reward finite, obs in range)
- **Integration** (`tests/integration/`) — end-to-end short training loops

### E2E tags (Playwright)

- `@smoke` wajib untuk jalur cepat CI: open app -> start run -> stream connected -> stop run.
- `@debug` opsional untuk investigasi lokal.
- Artifact saat gagal: screenshot, trace, dan browser console log.

Command:

```bash
cd apps/web && npm run e2e:smoke
cd apps/web && npm run e2e:debug
```

### Migration Closure Notes (v0.2.1)

- Web app menjadi canonical UX (web-first).
- TUI dipertahankan sebagai secondary UX, runnable via `make tui`.
- Full gate migrasi dirangkum di `make test-migration-gate` (backend unit+integration, frontend component test, dan e2e smoke).
- Checkpoint compatibility (`best.zip`, `gen_*.zip`) + retry flow tetap dijaga.

---

## Milestones

- [x] Data layer — fetch, normalize, dan cache OHLCV data
- [x] Environment — Gymnasium env dengan Sharpe-based reward + price return signal
- [x] Self-play loop — multi-generation PPO dengan checkpoint promotion
- [x] Web bootstrap — FastAPI backend + React Vite frontend skeleton
- [x] MultiDiscrete action space — partial position sizing (25%/50%/75%/100%)
- [x] Expanded observation — position + unrealized PnL channels
- [x] Win rate tracking — per-generation dan cumulative trade counts
- [x] 3-column chart area — Sharpe | Price | Action distribution
- [ ] Multi-asset support
- [ ] Backtesting module
- [ ] Strategy export

---

## License

TBD
