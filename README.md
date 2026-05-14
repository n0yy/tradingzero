# TradingZero

A Reinforcement Learning trading system that learns crypto strategies purely from self-play — no hand-crafted technical indicators. The agent evolves by beating previous versions of itself, producing increasingly sharp adaptive strategies over time.

Inspired by AlphaZero.

## How It Works

1. **Data Layer** — fetches OHLCV candles from exchanges (Binance, OKX, Bybit) via CCXT and normalizes them into rolling windows.
2. **Environment** — a custom Gymnasium env where the agent observes 60 candles and chooses Buy, Hold, or Sell. Reward is based on Sharpe ratio with a transaction cost penalty.
3. **Self-Play Training** — PPO (via Stable-Baselines3) trains against the best prior checkpoint. When the current agent's Sharpe exceeds the best by a threshold, it gets promoted.
4. **TUI Monitor** — a real-time terminal dashboard (Textual + Rich + Plotext) showing equity curves, metrics, and training logs.

## Architecture

```
main.py                 ← entry point & orchestrator
├── tui/app.py          ← real-time TUI monitor
├── agent/trainer.py    ← PPO self-play loop
├── env/crypto_env.py   ← Gymnasium environment
└── data/fetcher.py     ← CCXT data pipeline
```

## Tech Stack

| Category | Libraries |
|----------|-----------|
| RL / ML | PyTorch, Stable-Baselines3, Gymnasium |
| Data | CCXT, Pandas, NumPy |
| TUI | Textual, Rich, Plotext |
| Testing | Pytest, pytest-cov, pytest-mock, Hypothesis |
| Tooling | Weights & Biases, python-dotenv, Loguru |

## Getting Started

```bash
# Install dependencies
pip install -r requirements.txt

# Configure
cp config.yaml.example config.yaml
# Edit config.yaml with your exchange API keys and preferences

# Run training with TUI
python main.py
```

## Configuration

All settings live in `config.yaml`:

- **data** — exchange, symbol, timeframe, window size
- **env** — initial balance, transaction cost, episode length
- **agent** — PPO hyperparameters, total episodes, promote threshold
- **self_play** — checkpoint interval and directory
- **logging** — Weights & Biases project name

## Testing

```bash
# Run all tests with coverage
pytest --cov=tradingzero --cov-report=term-missing
```

Test layers:
- **Unit** (`tests/unit/`) — isolated function tests with mocked externals
- **Property-based** — Hypothesis tests for environment edge cases
- **Integration** (`tests/integration/`) — end-to-end short training loops

## Milestones

1. **Data Layer** — fetch, normalize, and cache OHLCV data
2. **Environment** — Gymnasium env with valid state/action/reward
3. **Self-Play Loop** — multi-generation training with checkpoint promotion
4. **TUI** — real-time monitoring dashboard

## License

TBD
