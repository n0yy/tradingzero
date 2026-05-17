import numpy as np
import pandas as pd
import gymnasium as gym
from gymnasium import spaces
from datetime import UTC, datetime

from data.fetcher import normalize_window


SIZE_MAP = {0: 0.25, 1: 0.50, 2: 0.75, 3: 1.00}
DIRECTION_LABELS = {0: "HOLD", 1: "BUY", 2: "SELL"}
MARKET_COLUMNS = ["open", "high", "low", "close", "volume"]


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
            low=-np.inf, high=np.inf, shape=(window_size, 7), dtype=np.float32
        )
        self.action_space = spaces.MultiDiscrete([3, 4])  # [direction, size]

        self._current_step = 0
        self._start_idx = 0
        self._position = 0.0
        self._balance = initial_balance
        self._returns: list[float] = []
        self._avg_entry_price = 0.0
        self._position_open_step: int | None = None

    def reset(self, seed=None, options=None):
        super().reset(seed=seed)
        max_start = len(self.data) - self.window_size - self.episode_length
        fixed_start = (options or {}).get('start_index')
        if fixed_start is not None:
            self._start_idx = int(max(0, min(fixed_start, max_start)))
        else:
            self._start_idx = int(self.np_random.integers(0, max(1, max_start)))
        self._current_step = 0
        self._position = 0.0
        self._balance = self.initial_balance
        self._returns = []
        self._avg_entry_price = 0.0
        self._position_open_step = None
        obs = self._get_obs()
        return obs, {}

    def _get_obs(self) -> np.ndarray:
        idx = self._start_idx + self._current_step
        window = self.data.iloc[idx: idx + self.window_size].copy()
        normalized = normalize_window(window[MARKET_COLUMNS])  # shape (window_size, 5)

        current_price = float(self.data.iloc[idx + self.window_size - 1]["close"])
        unrealized_pnl = self._compute_unrealized_return(current_price)

        obs = np.zeros((self.window_size, 7), dtype=np.float32)
        obs[:, :5] = normalized
        obs[:, 5] = self._position
        obs[:, 6] = unrealized_pnl
        return obs

    def _compute_unrealized_return(self, reference_price: float) -> float:
        if self._position <= 0.0 or self._avg_entry_price <= 0.0:
            return 0.0
        price_return = (reference_price - self._avg_entry_price) / self._avg_entry_price
        return float(price_return * self._position)

    def _compute_unrealized_pnl_usd(self, reference_price: float, balance_reference: float) -> float:
        return float(balance_reference * self._compute_unrealized_return(reference_price))

    def _compute_realized_pnl_usd(
        self,
        traded_fraction: float,
        execution_price: float,
        balance_reference: float,
    ) -> float:
        if traded_fraction <= 0.0 or self._avg_entry_price <= 0.0:
            return 0.0
        price_return = (execution_price - self._avg_entry_price) / self._avg_entry_price
        return float(balance_reference * traded_fraction * price_return)

    def _step_timestamp(self, idx: int) -> str:
        raw = self.data.iloc[idx + self.window_size - 1].get("timestamp")
        if raw is None or pd.isna(raw):
            return datetime.now(UTC).isoformat()
        return datetime.fromtimestamp(float(raw) / 1000.0, tz=UTC).isoformat()

    def step(self, action):
        action = np.asarray(action)
        direction = int(action[0])
        size = int(action[1])

        idx = self._start_idx + self._current_step
        current_price = float(self.data.iloc[idx + self.window_size - 1]["close"])
        next_price = float(self.data.iloc[idx + self.window_size]["close"])
        timestamp = self._step_timestamp(idx)

        delta = SIZE_MAP[size]
        prev_position = self._position
        balance_before = self._balance
        realized_pnl = 0.0

        if direction == 1:  # Buy
            new_position = min(self._position + delta, 1.0)
            traded = new_position - self._position
            if traded > 0:
                self._avg_entry_price = (
                    (self._avg_entry_price * self._position + current_price * traded) / new_position
                )
                if self._position_open_step is None:
                    self._position_open_step = self._current_step
            self._position = new_position
        elif direction == 2:  # Sell
            traded = min(delta, self._position)
            realized_pnl = self._compute_realized_pnl_usd(traded, current_price, balance_before)
            self._position = max(self._position - delta, 0.0)
            if self._position == 0.0:
                self._avg_entry_price = 0.0
                self._position_open_step = None
        # direction == 0: Hold — position unchanged

        traded = abs(self._position - prev_position)
        cost = self.transaction_cost * traded

        price_return = (next_price - current_price) / current_price if current_price != 0 else 0.0
        step_return = price_return * self._position - cost
        self._balance *= (1 + step_return)
        self._returns.append(step_return)

        executed_delta = self._position - prev_position
        transaction_outcome = (
            "BUY" if executed_delta > 0 else "SELL" if executed_delta < 0 else "NO_TRANSACTION"
        )
        is_transaction = transaction_outcome != "NO_TRANSACTION"
        fee_usd = balance_before * cost
        if transaction_outcome == "SELL":
            realized_pnl -= fee_usd
        executed_trade = None
        if is_transaction:
            executed_trade = {
                "action": transaction_outcome,
                "timestamp": timestamp,
                "execution_price": current_price,
                "size_percent": abs(executed_delta),
                "position_before": prev_position,
                "position_after": self._position,
                "notional_usd": balance_before * abs(executed_delta),
                "balance_before": balance_before,
                "balance_after": self._balance,
                "fee": fee_usd,
                "realized_pnl": realized_pnl,
                "unrealized_pnl_after": self._compute_unrealized_pnl_usd(next_price, self._balance),
                "hold_duration": (self._current_step - self._position_open_step) if self._position_open_step is not None else 0,
            }

        reward = self._compute_reward()
        # Outperformance vs half-weight buy-and-hold benchmark.
        # - Holding flat in a down market -> positive reward (avoided loss).
        # - Holding flat in an up market -> small negative reward (missed gain).
        # - Long position outperforming benchmark -> positive reward.
        # Cost is included in agent_return so trades must beat their friction.
        benchmark_return = price_return * self._position * 0.5
        agent_return = price_return * self._position - cost
        reward += (agent_return - benchmark_return) * 0.1

        self._current_step += 1
        terminated = self._balance <= 0
        truncated = self._current_step >= self.episode_length

        obs = self._get_obs()
        info = {
            "balance": self._balance,
            "position": self._position,
            "step": self._current_step,
            "cost": cost,
            "fee_usd": fee_usd,
            "price": current_price,
            "next_price": next_price,
            "timestamp": timestamp,
            "requested_direction": DIRECTION_LABELS[direction],
            "requested_size_percent": delta,
            "position_before": prev_position,
            "position_after": self._position,
            "executed_delta": executed_delta,
            "transaction_outcome": transaction_outcome,
            "is_transaction": is_transaction,
            "executed_trade": executed_trade,
            "realized_pnl": realized_pnl,
            "unrealized_pnl_after": self._compute_unrealized_pnl_usd(next_price, self._balance),
        }
        return obs, reward, terminated, truncated, info

    def _compute_reward(self, window: int = 100) -> float:
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
