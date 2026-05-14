import ccxt
import pandas as pd
import pytest
from unittest.mock import MagicMock, patch

from data.fetcher import fetch_ohlcv

MOCK_OHLCV = [
    [1700000000000 + i * 3600000, 30000 + i, 30100 + i, 29900 + i, 30050 + i, 100 + i]
    for i in range(100)
]


def test_fetch_ohlcv_returns_dataframe_with_correct_columns(mocker):
    mock_exchange = MagicMock()
    mock_exchange.fetch_ohlcv.return_value = MOCK_OHLCV
    mocker.patch("ccxt.binance", return_value=mock_exchange)

    result = fetch_ohlcv("binance", "BTC/USDT", "1h", limit=100)

    assert isinstance(result, pd.DataFrame)
    assert list(result.columns) == ["timestamp", "open", "high", "low", "close", "volume"]
    assert len(result) == 100


import numpy as np
from data.fetcher import normalize_window


def test_normalize_window_returns_correct_shape_and_dtype():
    df = pd.DataFrame(MOCK_OHLCV[:60], columns=["timestamp", "open", "high", "low", "close", "volume"])
    result = normalize_window(df)
    assert result.shape == (60, 6)
    assert result.dtype == np.float32


def test_normalize_window_values_in_range():
    df = pd.DataFrame(MOCK_OHLCV[:60], columns=["timestamp", "open", "high", "low", "close", "volume"])
    result = normalize_window(df)
    assert result.min() >= 0.0
    assert result.max() <= 1.0


def test_normalize_window_constant_column_does_not_produce_nan():
    data = [[1700000000000, 100.0, 100.0, 100.0, 100.0, 0.0]] * 60
    df = pd.DataFrame(data, columns=["timestamp", "open", "high", "low", "close", "volume"])
    result = normalize_window(df)
    assert not np.isnan(result).any()


from data.fetcher import cache_ohlcv, load_cache


def test_cache_round_trip(tmp_path):
    df = pd.DataFrame(MOCK_OHLCV[:60], columns=["timestamp", "open", "high", "low", "close", "volume"])
    path = tmp_path / "ohlcv.parquet"
    cache_ohlcv(df, str(path))
    loaded = load_cache(str(path))
    pd.testing.assert_frame_equal(df, loaded)


def test_load_cache_missing_file_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_cache(str(tmp_path / "nonexistent.parquet"))


def test_fetch_ohlcv_retries_on_rate_limit(mocker):
    mock_exchange = MagicMock()
    mock_exchange.fetch_ohlcv.side_effect = [
        ccxt.RateLimitExceeded("rate limit"),
        MOCK_OHLCV,
    ]
    mocker.patch("ccxt.binance", return_value=mock_exchange)
    mocker.patch("time.sleep")

    result = fetch_ohlcv("binance", "BTC/USDT", "1h", limit=100)

    assert isinstance(result, pd.DataFrame)
    assert mock_exchange.fetch_ohlcv.call_count == 2


def test_fetch_ohlcv_raises_after_max_retries(mocker):
    mock_exchange = MagicMock()
    mock_exchange.fetch_ohlcv.side_effect = ccxt.RateLimitExceeded("rate limit")
    mocker.patch("ccxt.binance", return_value=mock_exchange)
    mocker.patch("time.sleep")

    with pytest.raises(ccxt.RateLimitExceeded):
        fetch_ohlcv("binance", "BTC/USDT", "1h", limit=100)
