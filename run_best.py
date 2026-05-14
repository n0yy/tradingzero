"""
run_best.py — run the best promoted checkpoint against latest data.

Usage:
    uv run python run_best.py
    uv run python run_best.py --checkpoint agent/checkpoints/gen_0200.zip
    uv run python run_best.py --symbol BTC/USDT --timeframe 1h
"""

import argparse
from pathlib import Path

import numpy as np
import yaml
from dotenv import load_dotenv
from stable_baselines3 import PPO

from logger import logger


SIZE_LABELS = {0: "25%", 1: "50%", 2: "75%", 3: "100%"}
ACTION_COLORS = {0: "\033[90m", 1: "\033[92m", 2: "\033[91m"}
RESET = "\033[0m"


def format_action(action: np.ndarray) -> str:
    direction = int(action[0])
    size = int(action[1])
    if direction == 0:
        return "HOLD"
    elif direction == 1:
        return f"BUY {SIZE_LABELS[size]}"
    else:
        return f"SELL {SIZE_LABELS[size]}"


def check_compat(model: PPO, env) -> bool:
    model_obs = model.observation_space
    env_obs = env.observation_space
    model_act = model.action_space
    env_act = env.action_space

    ok = True
    if model_obs.shape != env_obs.shape:
        print(f"WARNING: obs space mismatch — checkpoint={model_obs.shape}, env={env_obs.shape}")
        ok = False
    if str(model_act) != str(env_act):
        print(f"WARNING: action space mismatch — checkpoint={model_act}, env={env_act}")
        ok = False
    return ok


def load_config(path: str = "config.yaml") -> dict:
    with open(path) as f:
        return yaml.safe_load(f)


def fetch_data(config: dict):
    from data.fetcher import fetch_ohlcv, load_cache, cache_ohlcv
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


def run(checkpoint: str, config: dict) -> None:
    from env.crypto_env import CryptoEnv

    data = fetch_data(config)
    env = CryptoEnv(
        data=data,
        window_size=config["data"]["window_size"],
        initial_balance=config["env"]["initial_balance"],
        transaction_cost=config["env"]["transaction_cost"],
        episode_length=config["env"]["episode_length"],
    )

    logger.info(f"Loading checkpoint: {checkpoint}")
    model = PPO.load(checkpoint, env=env)

    if not check_compat(model, env):
        logger.error("Checkpoint is incompatible with current env. Aborting.")
        return

    obs, _ = env.reset()
    done = False
    step = 0
    trades: list[dict] = []
    prev_action_str = ""

    print(f"\n{'─' * 60}")
    print(f"  TradingZero — Best Agent Inference")
    print(f"  Checkpoint : {checkpoint}")
    print(f"  Symbol     : {config['data']['symbol']} {config['data']['timeframe']}")
    print(f"  Balance    : ${config['env']['initial_balance']:,.2f}")
    print(f"{'─' * 60}\n")
    print(f"  {'Step':>5}  {'Action':<12}  {'Balance':>12}  {'PnL':>10}")
    print(f"  {'─'*5}  {'─'*12}  {'─'*12}  {'─'*10}")

    while not done:
        action, _ = model.predict(obs, deterministic=True)
        obs, reward, terminated, truncated, info = env.step(action)
        done = terminated or truncated
        step += 1

        balance = info["balance"]
        pnl = balance - config["env"]["initial_balance"]
        pnl_str = f"+${pnl:,.2f}" if pnl >= 0 else f"-${abs(pnl):,.2f}"
        action_str = format_action(action)
        color = ACTION_COLORS[int(action[0])]

        if action_str != prev_action_str or step % 50 == 0:
            print(f"  {step:>5}  {color}{action_str:<12}{RESET}  ${balance:>11,.2f}  {pnl_str:>10}")

        if action_str != prev_action_str and int(action[0]) in (1, 2):
            trades.append({"step": step, "action": action_str, "balance": balance})

        prev_action_str = action_str

    final_balance = info["balance"]
    pnl = final_balance - config["env"]["initial_balance"]
    pnl_pct = pnl / config["env"]["initial_balance"] * 100

    print(f"\n{'─' * 60}")
    print(f"  Final Balance : ${final_balance:,.2f}")
    pnl_color = "\033[92m" if pnl >= 0 else "\033[91m"
    print(f"  PnL           : {pnl_color}{'+' if pnl >= 0 else ''}{pnl:,.2f} ({pnl_pct:+.2f}%){RESET}")
    print(f"  Total Steps   : {step}")
    print(f"  Total Trades  : {len(trades)}")
    print(f"{'─' * 60}\n")


def main() -> None:
    load_dotenv()
    config = load_config()

    parser = argparse.ArgumentParser(description="Run best TradingZero checkpoint")
    parser.add_argument(
        "--checkpoint",
        default="agent/checkpoints/best.zip",
        help="Path to checkpoint zip (default: agent/checkpoints/best.zip)",
    )
    parser.add_argument("--symbol", help="Override symbol from config")
    parser.add_argument("--timeframe", help="Override timeframe from config")
    args = parser.parse_args()

    if args.symbol:
        config["data"]["symbol"] = args.symbol
    if args.timeframe:
        config["data"]["timeframe"] = args.timeframe

    if not Path(args.checkpoint).exists():
        logger.error(f"Checkpoint not found: {args.checkpoint}")
        return

    run(args.checkpoint, config)


if __name__ == "__main__":
    main()

