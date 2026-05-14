# TradingZero

A Reinforcement Learning trading system that learns crypto strategies purely from self-play — no hand-crafted technical indicators. The agent evolves by beating previous versions of itself, producing increasingly sharp adaptive strategies over time.

Inspired by AlphaZero.

## Status

Active development. Latest run (2026-05-14):
- Best Sharpe: **2.1152** @ generation 8
- Initial balance: $10,000 | tracked via real-time PnL dashboard
- Training on BTC/USDT 15m candles (Binance)

## How It Works

1. **Data Layer** — fetches OHLCV candles from exchanges (Binance, OKX, Bybit) via CCXT and normalizes them into rolling windows.
2. **Environment** — a custom Gymnasium env where the agent observes 60 candles and chooses Buy, Hold, or Sell. Reward is Sharpe ratio + immediate price return signal, with transaction cost penalty.
3. **Self-Play Training** — PPO (via Stable-Baselines3) trains across generations. When the current agent's Sharpe exceeds the best by a threshold, it gets promoted and saved as the new best checkpoint.
4. **TUI Monitor** — a real-time terminal dashboard (Textual + Rich) showing Sharpe chart, balance, PnL, and training logs.

## Architecture

```
main.py                 ← entry point & orchestrator
├── logger.py           ← shared logger (Loguru)
├── tui/app.py          ← real-time TUI dashboard
├── agent/trainer.py    ← PPO self-play loop
├── env/crypto_env.py   ← Gymnasium environment
└── data/fetcher.py     ← CCXT data pipeline
```

## Tech Stack

| Category | Libraries |
|----------|-----------|
| RL / ML | PyTorch, Stable-Baselines3, Gymnasium |
| Data | CCXT, Pandas, NumPy |
| TUI | Textual, Rich |
| Testing | Pytest, pytest-cov, pytest-mock, Hypothesis |
| Tooling | Weights & Biases, python-dotenv, Loguru |

## Getting Started

```bash
# Install dependencies (requires uv)
uv sync

# Configure
cp config.yaml.example config.yaml
# Edit config.yaml — set exchange, symbol, hyperparameters

# Run training with TUI
uv run python main.py
```

## Configuration

All settings live in `config.yaml`:

| Section | Key settings |
|---------|-------------|
| `data` | exchange, symbol, timeframe, window_size |
| `env` | initial_balance, transaction_cost, episode_length |
| `agent` | learning_rate, n_steps, batch_size, total_episodes, promote_threshold |
| `self_play` | checkpoint_interval, checkpoint_dir |
| `logging` | wandb, project_name |

## TUI Dashboard

The terminal dashboard updates in real-time every generation:

- **Metrics bar** — Generation, Progress %, Sharpe, Best Sharpe, Balance, PnL, Promotions, Status
- **Chart** — Sparkline of Sharpe ratio over generations (green = positive, red = negative)
- **Log** — Per-generation log with Sharpe, best Sharpe, and PnL

Press `q` to quit.

## Testing

```bash
uv run pytest tests/unit/ -v
```

Test layers:
- **Unit** (`tests/unit/`) — isolated tests for TUI components, env, data pipeline
- **Property-based** — Hypothesis tests for environment edge cases
- **Integration** (`tests/integration/`) — end-to-end short training loops

## Milestones

- [x] Data layer — fetch, normalize, and cache OHLCV data
- [x] Environment — Gymnasium env with Sharpe-based reward + price return signal
- [x] Self-play loop — multi-generation PPO with checkpoint promotion
- [x] TUI dashboard — real-time metrics, sparkline chart, PnL tracking
- [ ] Multi-asset support
- [ ] Backtesting module
- [ ] Strategy export

## License

TBD
