import time
from pathlib import Path

import ccxt
import numpy as np
import pandas as pd

MAX_RETRIES = 3
RETRY_DELAY = 1.0


def fetch_ohlcv(
    exchange_id: str,
    symbol: str,
    timeframe: str,
    limit: int = 17520,
) -> pd.DataFrame:
    """Fetch OHLCV data with pagination to get more than the API limit per request.

    Uses forward pagination: starts from a point in the past and fetches forward to present.
    """
    from datetime import datetime

    exchange_class = getattr(ccxt, exchange_id)
    exchange = exchange_class()

    # CCXT free API typically limits to 1000 candles per request
    # We paginate by starting in the past and moving forward
    MAX_PER_REQUEST = 1000

    # Parse timeframe to calculate milliseconds
    tf_map = {'1m': 60000, '5m': 300000, '15m': 900000, '30m': 1800000, '1h': 3600000, '4h': 14400000, '1d': 86400000}
    tf_ms = tf_map.get(timeframe, 900000)  # default to 15m

    # Calculate start time to fetch enough historical data
    now_ms = int(datetime.now().timestamp() * 1000)
    start_from = now_ms - (limit * tf_ms)

    all_candles = []
    current_since = start_from

    for attempt in range(MAX_RETRIES):
        try:
            while len(all_candles) < limit:
                remaining = limit - len(all_candles)
                batch_size = min(MAX_PER_REQUEST, remaining)

                raw = exchange.fetch_ohlcv(symbol, timeframe, limit=batch_size, since=current_since)
                if not raw:
                    break  # No more data available

                # Filter out duplicates (candles we already have)
                if all_candles:
                    raw = [c for c in raw if c[0] > all_candles[-1][0]]

                if not raw:
                    break

                all_candles.extend(raw)

                # Move `since` to after the latest candle we fetched
                current_since = raw[-1][0] + 1
                time.sleep(0.3)  # Rate limit friendly

            df = pd.DataFrame(all_candles, columns=["timestamp", "open", "high", "low", "close", "volume"])
            return df.drop_duplicates(subset=["timestamp"], keep="last").reset_index(drop=True)

        except ccxt.RateLimitExceeded:
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_DELAY * (attempt + 1))
            else:
                raise


def normalize_window(df: pd.DataFrame) -> np.ndarray:
    values = df.to_numpy(dtype=np.float32)
    # Use only past candles (all except the last) to compute normalization stats.
    # Including the current (last) candle would leak future information into the
    # observation because the window extends forward from the current step.
    ref = values[:-1] if len(values) > 1 else values
    min_vals = ref.min(axis=0)
    max_vals = ref.max(axis=0)
    ranges = max_vals - min_vals
    ranges[ranges == 0] = 1.0
    normalized = (values - min_vals) / ranges
    return normalized.astype(np.float32)


def cache_ohlcv(df: pd.DataFrame, path: str) -> None:
    df.to_parquet(path, index=False)


def load_cache(path: str) -> pd.DataFrame:
    if not Path(path).exists():
        raise FileNotFoundError(f"Cache file not found: {path}")
    return pd.read_parquet(path)
