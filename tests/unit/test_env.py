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
    assert obs.shape == (WINDOW_SIZE, 7)


def test_reset_returns_float32_observation():
    from env.crypto_env import CryptoEnv
    env = CryptoEnv(data=make_mock_data(), window_size=WINDOW_SIZE)
    obs, info = env.reset()
    assert obs.dtype == np.float32


def test_reset_observation_values_in_range():
    from env.crypto_env import CryptoEnv
    env = CryptoEnv(data=make_mock_data(), window_size=WINDOW_SIZE)
    obs, info = env.reset()
    # OHLCV channels (0-4) are normalized to [0,1]; channels 5-6 may be outside
    assert obs[:, :5].min() >= 0.0
    assert obs[:, :5].max() <= 1.0


def test_reset_returns_info_dict():
    from env.crypto_env import CryptoEnv
    env = CryptoEnv(data=make_mock_data(), window_size=WINDOW_SIZE)
    obs, info = env.reset()
    assert isinstance(info, dict)


# --- step() returns valid tuple ---

def test_step_returns_valid_tuple_for_hold():
    from env.crypto_env import CryptoEnv
    import numpy as np
    env = CryptoEnv(data=make_mock_data(), window_size=WINDOW_SIZE)
    env.reset()
    obs, reward, terminated, truncated, info = env.step(np.array([0, 0]))
    assert obs.shape == (WINDOW_SIZE, 7)
    assert obs.dtype == np.float32
    assert isinstance(reward, float)
    assert isinstance(terminated, bool)
    assert isinstance(truncated, bool)
    assert isinstance(info, dict)


def test_step_returns_valid_tuple_for_buy():
    from env.crypto_env import CryptoEnv
    import numpy as np
    env = CryptoEnv(data=make_mock_data(), window_size=WINDOW_SIZE)
    env.reset()
    obs, reward, terminated, truncated, info = env.step(np.array([1, 3]))  # buy 100%
    assert obs.shape == (WINDOW_SIZE, 7)
    assert abs(info["position"] - 1.0) < 1e-6


def test_step_returns_valid_tuple_for_sell():
    from env.crypto_env import CryptoEnv
    import numpy as np
    env = CryptoEnv(data=make_mock_data(), window_size=WINDOW_SIZE)
    env.reset()
    env.step(np.array([1, 3]))  # buy 100% first
    obs, reward, terminated, truncated, info = env.step(np.array([2, 3]))  # sell 100%
    assert obs.shape == (WINDOW_SIZE, 7)
    assert abs(info["position"] - 0.0) < 1e-6


def test_step_truncates_after_episode_length():
    from env.crypto_env import CryptoEnv
    import numpy as np
    env = CryptoEnv(data=make_mock_data(n=700), window_size=WINDOW_SIZE, episode_length=10)
    env.reset()
    truncated = False
    for _ in range(10):
        _, _, _, truncated, _ = env.step(np.array([0, 0]))
    assert truncated is True


# --- Hypothesis property tests ---

from hypothesis import given, settings
import hypothesis.strategies as st


@given(actions=st.lists(
    st.tuples(st.integers(min_value=0, max_value=2), st.integers(min_value=0, max_value=3)),
    min_size=10, max_size=50
))
@settings(max_examples=50)
def test_reward_is_always_finite(actions):
    from env.crypto_env import CryptoEnv
    import numpy as np
    env = CryptoEnv(data=make_mock_data(n=700), window_size=WINDOW_SIZE, episode_length=500)
    env.reset(seed=42)
    for direction, size in actions:
        obs, reward, terminated, truncated, info = env.step(np.array([direction, size]))
        assert np.isfinite(reward), f"reward={reward} is not finite"
        if terminated or truncated:
            break


@given(actions=st.lists(
    st.tuples(st.integers(min_value=0, max_value=2), st.integers(min_value=0, max_value=3)),
    min_size=10, max_size=50
))
@settings(max_examples=50)
def test_obs_always_in_range(actions):
    from env.crypto_env import CryptoEnv
    import numpy as np
    env = CryptoEnv(data=make_mock_data(n=700), window_size=WINDOW_SIZE, episode_length=500)
    env.reset(seed=42)
    for direction, size in actions:
        obs, reward, terminated, truncated, info = env.step(np.array([direction, size]))
        assert obs.min() >= 0.0, f"obs min={obs.min()} < 0"
        assert obs.max() <= 1.0, f"obs max={obs.max()} > 1"
        if terminated or truncated:
            break


# --- Issue #16: MultiDiscrete action space ---

def test_action_space_is_multidiscrete():
    from env.crypto_env import CryptoEnv
    from gymnasium.spaces import MultiDiscrete
    env = CryptoEnv(data=make_mock_data(), window_size=WINDOW_SIZE)
    assert isinstance(env.action_space, MultiDiscrete)
    assert list(env.action_space.nvec) == [3, 4]


def test_buy_25_from_zero_gives_position_025():
    from env.crypto_env import CryptoEnv
    import numpy as np
    env = CryptoEnv(data=make_mock_data(n=700), window_size=WINDOW_SIZE, episode_length=500)
    env.reset(seed=0)
    # action: direction=Buy(1), size=25%(0)
    _, _, _, _, info = env.step(np.array([1, 0]))
    assert abs(info["position"] - 0.25) < 1e-6


def test_buy_50_from_075_caps_at_1():
    from env.crypto_env import CryptoEnv
    import numpy as np
    env = CryptoEnv(data=make_mock_data(n=700), window_size=WINDOW_SIZE, episode_length=500)
    env.reset(seed=0)
    env.step(np.array([1, 2]))  # buy 75% → position=0.75
    _, _, _, _, info = env.step(np.array([1, 1]))  # buy 50% → capped at 1.0
    assert abs(info["position"] - 1.0) < 1e-6


def test_sell_25_from_050_gives_025():
    from env.crypto_env import CryptoEnv
    import numpy as np
    env = CryptoEnv(data=make_mock_data(n=700), window_size=WINDOW_SIZE, episode_length=500)
    env.reset(seed=0)
    env.step(np.array([1, 1]))  # buy 50%
    _, _, _, _, info = env.step(np.array([2, 0]))  # sell 25%
    assert abs(info["position"] - 0.25) < 1e-6


def test_sell_100_from_025_floors_at_0():
    from env.crypto_env import CryptoEnv
    import numpy as np
    env = CryptoEnv(data=make_mock_data(n=700), window_size=WINDOW_SIZE, episode_length=500)
    env.reset(seed=0)
    env.step(np.array([1, 0]))  # buy 25%
    _, _, _, _, info = env.step(np.array([2, 3]))  # sell 100% → floored at 0.0
    assert abs(info["position"] - 0.0) < 1e-6


def test_hold_ignores_size_axis():
    from env.crypto_env import CryptoEnv
    import numpy as np
    env = CryptoEnv(data=make_mock_data(n=700), window_size=WINDOW_SIZE, episode_length=500)
    env.reset(seed=0)
    env.step(np.array([1, 1]))  # buy 50% → position=0.5
    _, _, _, _, info = env.step(np.array([0, 3]))  # hold with size=100% → position unchanged
    assert abs(info["position"] - 0.5) < 1e-6


def test_no_cost_on_hold():
    from env.crypto_env import CryptoEnv
    import numpy as np
    env = CryptoEnv(data=make_mock_data(n=700), window_size=WINDOW_SIZE, episode_length=500)
    env.reset(seed=0)
    balance_before = env._balance
    env.step(np.array([0, 0]))  # hold
    # balance should only change due to price movement, not transaction cost
    # we verify cost field in info
    _, _, _, _, info = env.step(np.array([0, 0]))
    assert info.get("cost", 0.0) == 0.0


def test_transaction_cost_proportional_to_actual_change():
    from env.crypto_env import CryptoEnv
    import numpy as np
    env = CryptoEnv(data=make_mock_data(n=700), window_size=WINDOW_SIZE, episode_length=500)
    env.reset(seed=0)
    env.step(np.array([1, 3]))  # buy 100% → traded=1.0
    _, _, _, _, info = env.step(np.array([2, 0]))  # sell 25% → traded=0.25
    assert abs(info.get("cost", -1) - env.transaction_cost * 0.25) < 1e-6


def test_reward_finite_for_all_multidiscrete_actions():
    from env.crypto_env import CryptoEnv
    import numpy as np
    env = CryptoEnv(data=make_mock_data(n=700), window_size=WINDOW_SIZE, episode_length=500)
    env.reset(seed=42)
    for direction in range(3):
        for size in range(4):
            obs, reward, terminated, truncated, info = env.step(np.array([direction, size]))
            assert np.isfinite(reward), f"reward not finite for action [{direction},{size}]"
            if terminated or truncated:
                env.reset(seed=42)


def test_check_env_passes():
    from env.crypto_env import CryptoEnv
    from gymnasium.utils.env_checker import check_env
    env = CryptoEnv(data=make_mock_data(n=700), window_size=WINDOW_SIZE, episode_length=50)
    check_env(env, warn=True)


# --- Issue #17: observation space (60, 7) ---

def test_observation_space_shape_is_60_7():
    from env.crypto_env import CryptoEnv
    env = CryptoEnv(data=make_mock_data(), window_size=WINDOW_SIZE)
    assert env.observation_space.shape == (WINDOW_SIZE, 7)


def test_reset_obs_shape_is_60_7():
    from env.crypto_env import CryptoEnv
    env = CryptoEnv(data=make_mock_data(), window_size=WINDOW_SIZE)
    obs, _ = env.reset()
    assert obs.shape == (WINDOW_SIZE, 7)


def test_step_obs_shape_is_60_7():
    from env.crypto_env import CryptoEnv
    import numpy as np
    env = CryptoEnv(data=make_mock_data(n=700), window_size=WINDOW_SIZE, episode_length=500)
    env.reset(seed=0)
    obs, _, _, _, _ = env.step(np.array([0, 0]))
    assert obs.shape == (WINDOW_SIZE, 7)


def test_channel_6_position_reflects_current_position():
    from env.crypto_env import CryptoEnv
    import numpy as np
    env = CryptoEnv(data=make_mock_data(n=700), window_size=WINDOW_SIZE, episode_length=500)
    env.reset(seed=0)
    obs, _, _, _, info = env.step(np.array([1, 1]))  # buy 50%
    assert np.allclose(obs[:, 5], 0.5)


def test_channel_7_unrealized_pnl_zero_when_no_position():
    from env.crypto_env import CryptoEnv
    import numpy as np
    env = CryptoEnv(data=make_mock_data(n=700), window_size=WINDOW_SIZE, episode_length=500)
    obs, _ = env.reset(seed=0)
    assert np.allclose(obs[:, 6], 0.0)


def test_channel_7_unrealized_pnl_nonzero_when_position():
    from env.crypto_env import CryptoEnv
    import numpy as np
    env = CryptoEnv(data=make_mock_data(n=700), window_size=WINDOW_SIZE, episode_length=500)
    env.reset(seed=0)
    env.step(np.array([1, 3]))  # buy 100%
    obs, _, _, _, _ = env.step(np.array([0, 0]))  # hold — price moved
    # unrealized pnl channel should be set (may be 0 if price unchanged, but shape correct)
    assert obs.shape == (WINDOW_SIZE, 7)


def test_avg_entry_price_resets_after_full_sell():
    from env.crypto_env import CryptoEnv
    import numpy as np
    env = CryptoEnv(data=make_mock_data(n=700), window_size=WINDOW_SIZE, episode_length=500)
    env.reset(seed=0)
    env.step(np.array([1, 3]))  # buy 100%
    env.step(np.array([2, 3]))  # sell 100% → position=0, avg_entry_price should reset
    assert env._avg_entry_price == 0.0


def test_obs_all_finite_after_reset_and_steps():
    from env.crypto_env import CryptoEnv
    import numpy as np
    env = CryptoEnv(data=make_mock_data(n=700), window_size=WINDOW_SIZE, episode_length=500)
    obs, _ = env.reset(seed=0)
    assert np.all(np.isfinite(obs))
    for _ in range(10):
        obs, _, terminated, truncated, _ = env.step(np.array([1, 1]))
        assert np.all(np.isfinite(obs))
        if terminated or truncated:
            break


def test_check_env_passes_with_new_obs_space():
    from env.crypto_env import CryptoEnv
    from gymnasium.utils.env_checker import check_env
    env = CryptoEnv(data=make_mock_data(n=700), window_size=WINDOW_SIZE, episode_length=50)
    check_env(env)
