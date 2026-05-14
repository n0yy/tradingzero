import pytest
from unittest.mock import patch, MagicMock
from main import load_config, build_env, build_trainer


def test_load_config_returns_all_top_level_keys(tmp_path):
    config_file = tmp_path / "config.yaml"
    config_file.write_text(
        "data:\n  exchange: binance\nenv:\n  initial_balance: 10000\n"
        "agent:\n  algorithm: PPO\nself_play:\n  checkpoint_interval: 10\n"
        "logging:\n  wandb: true\n"
    )
    config = load_config(str(config_file))
    assert set(config.keys()) == {"data", "env", "agent", "self_play", "logging"}


def test_load_config_data_section(tmp_path):
    config_file = tmp_path / "config.yaml"
    config_file.write_text(
        "data:\n  exchange: binance\n  symbol: BTC/USDT\n  timeframe: 1h\n"
        "  window_size: 60\n  train_ratio: 0.8\n"
    )
    config = load_config(str(config_file))
    assert config["data"]["exchange"] == "binance"
    assert config["data"]["symbol"] == "BTC/USDT"
    assert config["data"]["window_size"] == 60
    assert config["data"]["train_ratio"] == 0.8


def test_load_config_missing_file_raises():
    with pytest.raises(FileNotFoundError):
        load_config("nonexistent.yaml")


def test_build_env_returns_crypto_env(tmp_path):
    import pandas as pd
    config = {
        "data": {"window_size": 60},
        "env": {"initial_balance": 10000, "transaction_cost": 0.001, "episode_length": 500},
    }
    rows = [
        [1700000000000 + i * 3600000, 30000 + i, 30100 + i, 29900 + i, 30050 + i, 100 + i]
        for i in range(700)
    ]
    data = pd.DataFrame(rows, columns=["timestamp", "open", "high", "low", "close", "volume"])
    from env.crypto_env import CryptoEnv
    env = build_env(config, data)
    assert isinstance(env, CryptoEnv)


def test_build_trainer_returns_trainer(tmp_path):
    import pandas as pd
    from queue import Queue
    config = {
        "data": {"window_size": 60},
        "env": {"initial_balance": 10000, "transaction_cost": 0.001, "episode_length": 500},
        "agent": {
            "total_episodes": 10,
            "learning_rate": 3e-4,
            "n_steps": 64,
            "batch_size": 32,
            "clip_range": 0.2,
            "promote_threshold": 0.05,
        },
        "self_play": {"checkpoint_interval": 5},
        "logging": {"wandb": False, "project_name": "test"},
    }
    rows = [
        [1700000000000 + i * 3600000, 30000 + i, 30100 + i, 29900 + i, 30050 + i, 100 + i]
        for i in range(700)
    ]
    data = pd.DataFrame(rows, columns=["timestamp", "open", "high", "low", "close", "volume"])
    env = build_env(config, data)
    queue = Queue()
    from agent.trainer import Trainer
    trainer = build_trainer(config, env, queue, str(tmp_path))
    assert isinstance(trainer, Trainer)
    assert trainer.wandb_project is None


def test_build_trainer_sets_wandb_project_when_enabled(tmp_path):
    import pandas as pd
    from queue import Queue
    config = {
        "data": {"window_size": 60},
        "env": {"initial_balance": 10000, "transaction_cost": 0.001, "episode_length": 500},
        "agent": {
            "total_episodes": 10,
            "learning_rate": 3e-4,
            "n_steps": 64,
            "batch_size": 32,
            "clip_range": 0.2,
            "promote_threshold": 0.05,
        },
        "self_play": {"checkpoint_interval": 5},
        "logging": {"wandb": True, "project_name": "tradingzero"},
    }
    rows = [
        [1700000000000 + i * 3600000, 30000 + i, 30100 + i, 29900 + i, 30050 + i, 100 + i]
        for i in range(700)
    ]
    data = pd.DataFrame(rows, columns=["timestamp", "open", "high", "low", "close", "volume"])
    env = build_env(config, data)
    queue = Queue()
    trainer = build_trainer(config, env, queue, str(tmp_path))
    assert trainer.wandb_project == "tradingzero"
