from __future__ import annotations

from pathlib import Path

import yaml
from stable_baselines3 import PPO

from logger import logger


def load_config(path: str = "config.yaml") -> dict:
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def fetch_data(config: dict):
    from data.fetcher import cache_ohlcv, fetch_ohlcv, load_cache

    cache_path = f"data/cache/{config['data']['symbol'].replace('/', '_')}_{config['data']['timeframe']}.parquet"
    Path(cache_path).parent.mkdir(parents=True, exist_ok=True)
    if Path(cache_path).exists():
        logger.info(f"Loading cached data from {cache_path}")
        return load_cache(cache_path)

    logger.info(f"Fetching OHLCV from {config['data']['exchange']}...")
    df = fetch_ohlcv(
        config["data"]["exchange"],
        config["data"]["symbol"],
        config["data"]["timeframe"],
        limit=2000,
    )
    cache_ohlcv(df, cache_path)
    return df


def check_compat(model: PPO, env) -> list[str]:
    issues: list[str] = []
    if model.observation_space.shape != env.observation_space.shape:
        issues.append(
            f"obs space mismatch — checkpoint={model.observation_space.shape}, env={env.observation_space.shape}"
        )
    if str(model.action_space) != str(env.action_space):
        issues.append(f"action space mismatch — checkpoint={model.action_space}, env={env.action_space}")
    return issues


def run_battle(checkpoint: str, config: dict) -> dict:
    from env.crypto_env import CryptoEnv

    checkpoint_path = Path(checkpoint)
    if not checkpoint_path.exists():
        raise FileNotFoundError(f"checkpoint not found: {checkpoint}")

    data = fetch_data(config)
    env = CryptoEnv(
        data=data,
        window_size=config["data"]["window_size"],
        initial_balance=config["env"]["initial_balance"],
        transaction_cost=config["env"]["transaction_cost"],
        episode_length=config["env"]["episode_length"],
    )

    logger.info(f"Loading checkpoint for battle: {checkpoint}")
    model = PPO.load(str(checkpoint_path), env=env)
    compat_issues = check_compat(model, env)
    if compat_issues:
        raise ValueError("; ".join(compat_issues))

    obs, _ = env.reset()
    done = False
    step = 0
    initial_balance = float(config["env"]["initial_balance"])
    transaction_distribution = {"buy": 0, "sell": 0, "no_transaction": 0}
    trade_outcomes = {"winning": 0, "losing": 0, "flat": 0}
    executed_trades: list[dict] = []
    price_series: list[float] = []
    equity_curve: list[float] = [initial_balance]

    while not done:
        action, _ = model.predict(obs, deterministic=True)
        obs, _reward, terminated, truncated, info = env.step(action)
        done = terminated or truncated
        step += 1

        price = float(info.get("price", 0.0))
        balance = float(info.get("balance", initial_balance))
        transaction_outcome = str(info.get("transaction_outcome", "NO_TRANSACTION"))
        executed_trade = info.get("executed_trade")

        price_series.append(price)
        equity_curve.append(balance)

        if transaction_outcome == "BUY":
            transaction_distribution["buy"] += 1
        elif transaction_outcome == "SELL":
            transaction_distribution["sell"] += 1
        else:
            transaction_distribution["no_transaction"] += 1

        if executed_trade is not None:
            trade_payload = dict(executed_trade)
            executed_trades.append(trade_payload)
            if trade_payload.get("action") == "SELL":
                realized_pnl = float(trade_payload.get("realized_pnl", 0.0))
                if realized_pnl > 0:
                    trade_outcomes["winning"] += 1
                elif realized_pnl < 0:
                    trade_outcomes["losing"] += 1
                else:
                    trade_outcomes["flat"] += 1

    final_balance = float(equity_curve[-1])
    pnl = final_balance - initial_balance
    pnl_pct = pnl / initial_balance if initial_balance else 0.0
    realized_exits = sum(trade_outcomes.values())
    trade_win_rate = trade_outcomes["winning"] / realized_exits if realized_exits else 0.0

    return {
        "checkpoint": str(checkpoint_path),
        "symbol": config["data"]["symbol"],
        "timeframe": config["data"]["timeframe"],
        "initial_balance": initial_balance,
        "final_balance": final_balance,
        "pnl": pnl,
        "pnl_pct": pnl_pct,
        "total_steps": step,
        "total_trades": len(executed_trades),
        "trade_win_rate": trade_win_rate,
        "winning_trades": trade_outcomes["winning"],
        "losing_trades": trade_outcomes["losing"],
        "flat_trades": trade_outcomes["flat"],
        "transaction_distribution": transaction_distribution,
        "price_series": price_series,
        "equity_curve": equity_curve,
        "executed_trades": executed_trades,
    }
