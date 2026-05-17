from __future__ import annotations

import numpy as np
import pandas as pd

from env.crypto_env import CryptoEnv


def _run_episode(env: CryptoEnv, action_fn, start_index: int | None = None) -> dict:
    options = {"start_index": start_index} if start_index is not None else None
    obs, _ = env.reset(options=options)
    done = False
    balances: list[float] = [env.initial_balance]
    while not done:
        action = action_fn(env, obs)
        obs, _, terminated, truncated, info = env.step(action)
        balances.append(float(info["balance"]))
        done = terminated or truncated
    returns = np.diff(balances) / np.array(balances[:-1], dtype=np.float32)
    std = float(np.std(returns))
    sharpe = float(np.mean(returns) / std) if std > 0 else 0.0
    sharpe = sharpe if np.isfinite(sharpe) else 0.0
    return {
        "final_balance": balances[-1],
        "pnl": balances[-1] - env.initial_balance,
        "sharpe": sharpe,
    }


def _random_action(env: CryptoEnv, obs) -> np.ndarray:
    return env.action_space.sample()


def _buy_and_hold_action(env: CryptoEnv, obs) -> np.ndarray:
    if env._position < 1.0:
        return np.array([1, 3])  # BUY 100%
    return np.array([0, 0])  # HOLD


def compute_baselines(
    data: pd.DataFrame,
    config: dict,
    anchors: list[dict],
    seed: int = 42,
) -> dict:
    env = CryptoEnv(
        data=data,
        window_size=int(config["data"]["window_size"]),
        initial_balance=float(config["env"]["initial_balance"]),
        transaction_cost=float(config["env"]["transaction_cost"]),
        episode_length=int(config["env"]["episode_length"]),
    )

    random_sharpes: list[float] = []
    bah_sharpes: list[float] = []

    for anchor in anchors:
        start_index = anchor.get("start_index")

        env.reset(seed=seed)
        random_result = _run_episode(env, _random_action, start_index)
        random_sharpes.append(random_result["sharpe"])

        env.reset(seed=seed)
        bah_result = _run_episode(env, _buy_and_hold_action, start_index)
        bah_sharpes.append(bah_result["sharpe"])

    return {
        "random_agent_sharpe": float(np.mean(random_sharpes)) if random_sharpes else 0.0,
        "buy_and_hold_sharpe": float(np.mean(bah_sharpes)) if bah_sharpes else 0.0,
    }
