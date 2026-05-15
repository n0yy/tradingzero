"""
run_best.py — run the best promoted checkpoint against latest data.

Usage:
    uv run python run_best.py
    uv run python run_best.py --checkpoint agent/checkpoints/gen_0200.zip
    uv run python run_best.py --symbol BTC/USDT --timeframe 1h
"""

import argparse
from pathlib import Path

from dotenv import load_dotenv

from backend.battle_runtime import load_config, run_battle


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
        raise FileNotFoundError(f"Checkpoint not found: {args.checkpoint}")

    result = run_battle(args.checkpoint, config)

    print(f"\n{'─' * 60}")
    print("  TradingZero — Best Agent Inference")
    print(f"  Checkpoint : {result['checkpoint']}")
    print(f"  Symbol     : {result['symbol']} {result['timeframe']}")
    print(f"  Balance    : ${result['initial_balance']:,.2f}")
    print(f"{'─' * 60}\n")
    print(f"  Final Balance : ${result['final_balance']:,.2f}")
    pnl = float(result["pnl"])
    pnl_pct = float(result["pnl_pct"]) * 100
    pnl_color = "\033[92m" if pnl >= 0 else "\033[91m"
    print(f"  PnL           : {pnl_color}{'+' if pnl >= 0 else ''}{pnl:,.2f} ({pnl_pct:+.2f}%){chr(27)}[0m")
    print(f"  Total Steps   : {result['total_steps']}")
    print(f"  Total Trades  : {result['total_trades']}")
    print(f"  Trade Win %   : {result['trade_win_rate'] * 100:.2f}%")
    print(f"{'─' * 60}\n")


if __name__ == "__main__":
    main()
