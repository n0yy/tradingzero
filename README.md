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
4. **TUI Monitor** — terminal dashboard real-time (Textual + Rich) menampilkan Sharpe chart, price chart, distribusi aksi, balance, PnL, dan win rate.

---

## Architecture

```
main.py                 ← entry point & orchestrator
├── logger.py           ← shared logger (Loguru)
├── data/fetcher.py     ← CCXT data pipeline + normalisasi
├── env/crypto_env.py   ← Gymnasium environment
│     observation: Box(60, 7)  — OHLCV + position + unrealized_pnl
│     action:      MultiDiscrete([3, 4])  — direction × size
├── agent/trainer.py    ← PPO self-play loop
│     _evaluate()       — win_rate, action_counts, price_series
│     _notify()         → update_queue → TUI
├── tui/app.py          ← real-time TUI dashboard
│     ChartArea         — Sharpe (40%) | Price (40%) | Action (20%)
│     MetricsBar        — Generation | Sharpe | Balance | PnL | WinRate | ...
└── run_best.py         ← inference runner + compat check
```

---

## Tech Stack

| Category | Libraries |
|----------|-----------|
| RL / ML | PyTorch, Stable-Baselines3, Gymnasium |
| Data | CCXT, Pandas, NumPy |
| TUI | Textual, Rich, plotext |
| Testing | Pytest, pytest-cov, pytest-mock, Hypothesis |
| Tooling | Weights & Biases, python-dotenv, Loguru |

---

## Getting Started

```bash
# Install dependencies (requires uv)
uv sync

# Configure
cp config.yaml.example config.yaml
# Edit config.yaml — set exchange, symbol, hyperparameters

# Run training with TUI
uv run python main.py

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

## TUI Dashboard

Terminal dashboard update real-time setiap generasi:

- **Metrics bar** — Generation, Progress %, Sharpe, Best Sharpe, Balance, PnL, Win Rate, Promotions, Status
- **Sharpe Panel** — sparkline Sharpe ratio lintas generasi (hijau = positif, merah = negatif)
- **Price Panel** — line chart harga episode terakhir + marker BUY ▲ / SELL ▼
- **Action Panel** — distribusi BUY/HOLD/SELL, last action, cumulative trades
- **Log** — log per-generasi dengan Sharpe, PnL, dan win rate

Tekan `q` untuk keluar.

---

## Testing

```bash
uv run pytest tests/unit/ -v
uv run pytest tests/integration/ -v
```

Test layers:
- **Unit** (`tests/unit/`) — isolated tests untuk TUI components, env, data pipeline, trainer, run_best
- **Property-based** — Hypothesis tests untuk edge case environment (reward finite, obs in range)
- **Integration** (`tests/integration/`) — end-to-end short training loops

---

## Milestones

- [x] Data layer — fetch, normalize, dan cache OHLCV data
- [x] Environment — Gymnasium env dengan Sharpe-based reward + price return signal
- [x] Self-play loop — multi-generation PPO dengan checkpoint promotion
- [x] TUI dashboard — real-time metrics, sparkline chart, PnL tracking
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
