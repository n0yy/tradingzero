import numpy as np
import pandas as pd
import pytest

WINDOW_SIZE = 60

def make_mock_data(n=200):
    rows = [
        [1700000000000 + i * 3600000, 30000 + i, 30100 + i, 29900 + i, 30050 + i, 100 + i]
        for i in range(n)
    ]
    return pd.DataFrame(rows, columns=["timestamp", "open", "high", "low", "close", "volume"])


# --- Tracer bullet: reset() ---

def test_reset_returns_observation_with_correct_shape():
    from env.crypto_env import CryptoEnv
    env = CryptoEnv(data=make_mock_data(), window_size=WINDOW_SIZE)
    obs, info = env.reset()
    assert obs.shape == (WINDOW_SIZE, 6)


def test_reset_returns_float32_observation():
    from env.crypto_env import CryptoEnv
    env = CryptoEnv(data=make_mock_data(), window_size=WINDOW_SIZE)
    obs, info = env.reset()
    assert obs.dtype == np.float32


def test_reset_observation_values_in_range():
    from env.crypto_env import CryptoEnv
    env = CryptoEnv(data=make_mock_data(), window_size=WINDOW_SIZE)
    obs, info = env.reset()
    assert obs.min() >= 0.0
    assert obs.max() <= 1.0


def test_reset_returns_info_dict():
    from env.crypto_env import CryptoEnv
    env = CryptoEnv(data=make_mock_data(), window_size=WINDOW_SIZE)
    obs, info = env.reset()
    assert isinstance(info, dict)


# --- step() returns valid tuple ---

def test_step_returns_valid_tuple_for_hold():
    from env.crypto_env import CryptoEnv
    env = CryptoEnv(data=make_mock_data(), window_size=WINDOW_SIZE)
    env.reset()
    obs, reward, terminated, truncated, info = env.step(0)
    assert obs.shape == (WINDOW_SIZE, 6)
    assert obs.dtype == np.float32
    assert isinstance(reward, float)
    assert isinstance(terminated, bool)
    assert isinstance(truncated, bool)
    assert isinstance(info, dict)


def test_step_returns_valid_tuple_for_buy():
    from env.crypto_env import CryptoEnv
    env = CryptoEnv(data=make_mock_data(), window_size=WINDOW_SIZE)
    env.reset()
    obs, reward, terminated, truncated, info = env.step(1)
    assert obs.shape == (WINDOW_SIZE, 6)
    assert info["position"] == 1.0


def test_step_returns_valid_tuple_for_sell():
    from env.crypto_env import CryptoEnv
    env = CryptoEnv(data=make_mock_data(), window_size=WINDOW_SIZE)
    env.reset()
    env.step(1)  # buy first
    obs, reward, terminated, truncated, info = env.step(2)
    assert obs.shape == (WINDOW_SIZE, 6)
    assert info["position"] == 0.0


def test_step_truncates_after_episode_length():
    from env.crypto_env import CryptoEnv
    env = CryptoEnv(data=make_mock_data(n=700), window_size=WINDOW_SIZE, episode_length=10)
    env.reset()
    truncated = False
    for _ in range(10):
        _, _, _, truncated, _ = env.step(0)
    assert truncated is True


# --- Hypothesis property tests ---

from hypothesis import given, settings
import hypothesis.strategies as st


@given(actions=st.lists(st.integers(min_value=0, max_value=2), min_size=10, max_size=50))
@settings(max_examples=50)
def test_reward_is_always_finite(actions):
    from env.crypto_env import CryptoEnv
    env = CryptoEnv(data=make_mock_data(n=700), window_size=WINDOW_SIZE, episode_length=500)
    env.reset(seed=42)
    for action in actions:
        obs, reward, terminated, truncated, info = env.step(action)
        assert np.isfinite(reward), f"reward={reward} is not finite"
        if terminated or truncated:
            break


@given(actions=st.lists(st.integers(min_value=0, max_value=2), min_size=10, max_size=50))
@settings(max_examples=50)
def test_obs_always_in_range(actions):
    from env.crypto_env import CryptoEnv
    env = CryptoEnv(data=make_mock_data(n=700), window_size=WINDOW_SIZE, episode_length=500)
    env.reset(seed=42)
    for action in actions:
        obs, reward, terminated, truncated, info = env.step(action)
        assert obs.min() >= 0.0, f"obs min={obs.min()} < 0"
        assert obs.max() <= 1.0, f"obs max={obs.max()} > 1"
        if terminated or truncated:
            break
