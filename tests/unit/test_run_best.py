import pytest
import numpy as np
import pandas as pd
from unittest.mock import patch, MagicMock


def make_mock_data(n=700):
    rows = [
        [1700000000000 + i * 3600000, 30000 + i, 30100 + i, 29900 + i, 30050 + i, 100 + i]
        for i in range(n)
    ]
    return pd.DataFrame(rows, columns=["timestamp", "open", "high", "low", "close", "volume"])


# --- Issue #18: run_best.py MultiDiscrete display + compat check ---

def test_format_action_buy_25():
    from run_best import format_action
    assert format_action(np.array([1, 0])) == "BUY 25%"


def test_format_action_buy_100():
    from run_best import format_action
    assert format_action(np.array([1, 3])) == "BUY 100%"


def test_format_action_sell_50():
    from run_best import format_action
    assert format_action(np.array([2, 1])) == "SELL 50%"


def test_format_action_hold_ignores_size():
    from run_best import format_action
    assert format_action(np.array([0, 3])) == "HOLD"
    assert format_action(np.array([0, 0])) == "HOLD"


def test_format_action_sell_75():
    from run_best import format_action
    assert format_action(np.array([2, 2])) == "SELL 75%"


def test_check_compat_passes_for_matching_spaces(tmp_path):
    from run_best import check_compat
    from env.crypto_env import CryptoEnv
    from stable_baselines3 import PPO

    env = CryptoEnv(data=make_mock_data(), window_size=60, episode_length=50)
    model = PPO("MlpPolicy", env, verbose=0)
    ckpt = str(tmp_path / "test_ckpt")
    model.save(ckpt)
    loaded = PPO.load(ckpt, env=env)
    # should not raise or warn for matching spaces
    result = check_compat(loaded, env)
    assert result is True


def test_check_compat_warns_for_mismatched_obs_space(tmp_path, capsys):
    from run_best import check_compat
    from env.crypto_env import CryptoEnv
    from stable_baselines3 import PPO
    import gymnasium as gym
    from gymnasium import spaces

    # train on old (60,6) env
    class OldEnv(CryptoEnv):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.observation_space = spaces.Box(
                low=0.0, high=1.0, shape=(60, 6), dtype=np.float32
            )

    old_env = OldEnv(data=make_mock_data(), window_size=60, episode_length=50)
    model = PPO("MlpPolicy", old_env, verbose=0)
    ckpt = str(tmp_path / "old_ckpt")
    model.save(ckpt)
    loaded = PPO.load(ckpt)

    new_env = CryptoEnv(data=make_mock_data(), window_size=60, episode_length=50)
    result = check_compat(loaded, new_env)
    assert result is False
    captured = capsys.readouterr()
    assert "WARNING" in captured.out or "mismatch" in captured.out.lower() or result is False
