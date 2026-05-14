import numpy as np
import pandas as pd
import gymnasium as gym
from gymnasium import spaces

from data.fetcher import normalize_window


class CryptoEnv(gym.Env):
    metadata = {"render_modes": []}

    def __init__(
        self,
        data: pd.DataFrame,
        window_size: int = 60,
        initial_balance: float = 10000.0,
        transaction_cost: float = 0.001,
        episode_length: int = 500,
    ):
        super().__init__()
        self.data = data.reset_index(drop=True)
        self.window_size = window_size
        self.initial_balance = initial_balance
        self.transaction_cost = transaction_cost
        self.episode_length = episode_length

        self.observation_space = spaces.Box(
            low=0.0, high=1.0, shape=(window_size, 6), dtype=np.float32
        )
        self.action_space = spaces.Discrete(3)  # 0=Hold, 1=Buy, 2=Sell

        self._current_step = 0
        self._start_idx = 0
        self._position = 0.0
        self._balance = initial_balance
        self._returns: list[float] = []

    def reset(self, seed=None, options=None):
        super().reset(seed=seed)
        max_start = len(self.data) - self.window_size - self.episode_length
        self._start_idx = int(self.np_random.integers(0, max(1, max_start)))
        self._current_step = 0
        self._position = 0.0
        self._balance = self.initial_balance
        self._returns = []
        obs = self._get_obs()
        return obs, {}

    def _get_obs(self) -> np.ndarray:
        idx = self._start_idx + self._current_step
        window = self.data.iloc[idx: idx + self.window_size].copy()
        normalized = normalize_window(window)
        normalized[:, -1] = self._position
        return normalized.astype(np.float32)

    def step(self, action: int):
        idx = self._start_idx + self._current_step
        current_price = float(self.data.iloc[idx + self.window_size - 1]["close"])
        next_price = float(self.data.iloc[idx + self.window_size]["close"])

        prev_position = self._position
        cost = 0.0

        if action == 1 and self._position == 0.0:
            self._position = 1.0
            cost = self.transaction_cost
        elif action == 2 and self._position == 1.0:
            self._position = 0.0
            cost = self.transaction_cost

        price_return = (next_price - current_price) / current_price if current_price != 0 else 0.0
        step_return = price_return * self._position - cost
        self._balance *= (1 + step_return)
        self._returns.append(step_return)

        reward = self._compute_reward()
        # add small immediate signal so agent gets gradient even when holding
        reward += price_return * self._position * 0.1

        self._current_step += 1
        terminated = self._balance <= 0
        truncated = self._current_step >= self.episode_length

        obs = self._get_obs()
        info = {
            "balance": self._balance,
            "position": self._position,
            "step": self._current_step,
        }
        return obs, reward, terminated, truncated, info

    def _compute_reward(self, window: int = 20) -> float:
        if len(self._returns) < 2:
            return 0.0
        recent = np.array(self._returns[-window:], dtype=np.float32)
        mean = np.mean(recent)
        std = np.std(recent)
        if std == 0:
            return 0.0
        sharpe = float(mean / std)
        if not np.isfinite(sharpe):
            return 0.0
        return sharpe
