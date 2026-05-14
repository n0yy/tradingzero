import numpy as np
import pandas as pd
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch


def make_mock_data(n=700):
    rows = [
        [1700000000000 + i * 3600000, 30000 + i, 30100 + i, 29900 + i, 30050 + i, 100 + i]
        for i in range(n)
    ]
    return pd.DataFrame(rows, columns=["timestamp", "open", "high", "low", "close", "volume"])


# --- Tracer bullet: Trainer instantiates ---

def test_trainer_instantiates(tmp_path):
    from env.crypto_env import CryptoEnv
    from agent.trainer import Trainer
    env = CryptoEnv(data=make_mock_data(), window_size=60, episode_length=50)
    trainer = Trainer(env=env, checkpoint_dir=str(tmp_path), total_generations=2)
    assert trainer is not None


def test_trainer_has_best_sharpe_minus_inf_initially(tmp_path):
    from env.crypto_env import CryptoEnv
    from agent.trainer import Trainer
    env = CryptoEnv(data=make_mock_data(), window_size=60, episode_length=50)
    trainer = Trainer(env=env, checkpoint_dir=str(tmp_path), total_generations=2)
    assert trainer.best_sharpe == -np.inf


# --- Checkpoint logic ---

def test_save_checkpoint_creates_file(tmp_path):
    from env.crypto_env import CryptoEnv
    from agent.trainer import Trainer
    env = CryptoEnv(data=make_mock_data(), window_size=60, episode_length=50)
    trainer = Trainer(env=env, checkpoint_dir=str(tmp_path), total_generations=1)
    trainer._model = trainer._build_model()
    ckpt = trainer._save_checkpoint(trainer._model, "test_ckpt")
    assert (tmp_path / "test_ckpt.zip").exists()


def test_validate_checkpoint_does_not_raise(tmp_path):
    from env.crypto_env import CryptoEnv
    from agent.trainer import Trainer
    env = CryptoEnv(data=make_mock_data(), window_size=60, episode_length=50)
    trainer = Trainer(env=env, checkpoint_dir=str(tmp_path), total_generations=1)
    trainer._model = trainer._build_model()
    ckpt = trainer._save_checkpoint(trainer._model, "valid_ckpt")
    trainer._validate_checkpoint(ckpt)  # should not raise


def test_prune_keeps_only_last_n(tmp_path):
    from env.crypto_env import CryptoEnv
    from agent.trainer import Trainer
    env = CryptoEnv(data=make_mock_data(), window_size=60, episode_length=50)
    trainer = Trainer(env=env, checkpoint_dir=str(tmp_path), total_generations=1)
    trainer._model = trainer._build_model()
    for i in range(1, 6):
        trainer._save_checkpoint(trainer._model, f"gen_{i:04d}")
    trainer._prune_old_checkpoints(keep=3)
    remaining = sorted(tmp_path.glob("gen_*.zip"))
    assert len(remaining) == 3
    assert remaining[-1].name == "gen_0005.zip"


# --- Promotion logic ---

def test_promotion_triggers_when_sharpe_improves(tmp_path, mocker):
    from env.crypto_env import CryptoEnv
    from agent.trainer import Trainer
    env = CryptoEnv(data=make_mock_data(), window_size=60, episode_length=50)
    trainer = Trainer(
        env=env,
        checkpoint_dir=str(tmp_path),
        total_generations=2,
        promote_threshold=0.05,
        n_steps=64,
        batch_size=32,
    )
    # gen 1: sets baseline=1.0, gen 2: 2.0 - 1.0 = 1.0 >= 0.05 → promote
    mocker.patch.object(trainer, "_evaluate", side_effect=[{"sharpe": 1.0, "final_balance": 10000.0, "pnl": 0.0, "initial_balance": 10000.0}, {"sharpe": 2.0, "final_balance": 10000.0, "pnl": 0.0, "initial_balance": 10000.0}])
    trainer.run()
    assert trainer.best_sharpe == 2.0
    assert (tmp_path / "best.zip").exists()


def test_promotion_does_not_trigger_below_threshold(tmp_path, mocker):
    from env.crypto_env import CryptoEnv
    from agent.trainer import Trainer
    env = CryptoEnv(data=make_mock_data(), window_size=60, episode_length=50)
    trainer = Trainer(
        env=env,
        checkpoint_dir=str(tmp_path),
        total_generations=1,
        promote_threshold=0.5,
        n_steps=64,
        batch_size=32,
    )
    # gen 1 sets baseline=0.1, gen 2: 0.15 - 0.1 = 0.05 < 0.5 threshold → no promote
    mocker.patch.object(trainer, "_evaluate", side_effect=[{"sharpe": 0.1, "final_balance": 10000.0, "pnl": 0.0, "initial_balance": 10000.0}, {"sharpe": 0.15, "final_balance": 10000.0, "pnl": 0.0, "initial_balance": 10000.0}])
    trainer = Trainer(
        env=env,
        checkpoint_dir=str(tmp_path),
        total_generations=2,
        promote_threshold=0.5,
        n_steps=64,
        batch_size=32,
    )
    mocker.patch.object(trainer, "_evaluate", side_effect=[{"sharpe": 0.1, "final_balance": 10000.0, "pnl": 0.0, "initial_balance": 10000.0}, {"sharpe": 0.15, "final_balance": 10000.0, "pnl": 0.0, "initial_balance": 10000.0}])
    trainer.run()
    assert not (tmp_path / "best.zip").exists()


def test_update_queue_receives_generation_payload(tmp_path, mocker):
    from queue import Queue
    from env.crypto_env import CryptoEnv
    from agent.trainer import Trainer
    env = CryptoEnv(data=make_mock_data(), window_size=60, episode_length=50)
    queue = Queue()
    trainer = Trainer(
        env=env,
        checkpoint_dir=str(tmp_path),
        total_generations=2,
        promote_threshold=10.0,
        n_steps=64,
        batch_size=32,
        update_queue=queue,
    )
    mocker.patch.object(trainer, "_evaluate", return_value={"sharpe": 0.1, "final_balance": 10000.0, "pnl": 0.0, "initial_balance": 10000.0})
    trainer.run()
    assert queue.qsize() == 2
    payload = queue.get()
    assert "generation" in payload
    assert "current_sharpe" in payload
    assert "best_sharpe" in payload


# --- Issue #10: action metrics & win rate ---

def test_evaluate_returns_win_rate(tmp_path):
    from env.crypto_env import CryptoEnv
    from agent.trainer import Trainer
    env = CryptoEnv(data=make_mock_data(), window_size=60, episode_length=50)
    trainer = Trainer(env=env, checkpoint_dir=str(tmp_path), total_generations=1)
    trainer._model = trainer._build_model()
    result = trainer._evaluate(trainer._model, n_eval_episodes=2)
    assert "win_rate" in result
    assert 0.0 <= result["win_rate"] <= 1.0


def test_evaluate_win_rate_all_profitable(tmp_path, mocker):
    from env.crypto_env import CryptoEnv
    from agent.trainer import Trainer
    env = CryptoEnv(data=make_mock_data(), window_size=60, episode_length=50)
    trainer = Trainer(env=env, checkpoint_dir=str(tmp_path), total_generations=1)
    trainer._model = trainer._build_model()
    initial = env.initial_balance
    mocker.patch.object(env, "reset", return_value=(np.zeros((60, 7), dtype=np.float32), {}))
    mocker.patch.object(env, "step", return_value=(
        np.zeros((60, 7), dtype=np.float32), 0.0, False, True,
        {"balance": initial + 100.0}
    ))
    result = trainer._evaluate(trainer._model, n_eval_episodes=3)
    assert result["win_rate"] == 1.0


def test_evaluate_win_rate_all_losing(tmp_path, mocker):
    from env.crypto_env import CryptoEnv
    from agent.trainer import Trainer
    env = CryptoEnv(data=make_mock_data(), window_size=60, episode_length=50)
    trainer = Trainer(env=env, checkpoint_dir=str(tmp_path), total_generations=1)
    trainer._model = trainer._build_model()
    initial = env.initial_balance
    mocker.patch.object(env, "reset", return_value=(np.zeros((60, 7), dtype=np.float32), {}))
    mocker.patch.object(env, "step", return_value=(
        np.zeros((60, 7), dtype=np.float32), 0.0, False, True,
        {"balance": initial - 100.0}
    ))
    result = trainer._evaluate(trainer._model, n_eval_episodes=3)
    assert result["win_rate"] == 0.0


def test_evaluate_returns_action_counts(tmp_path):
    from env.crypto_env import CryptoEnv
    from agent.trainer import Trainer
    env = CryptoEnv(data=make_mock_data(), window_size=60, episode_length=50)
    trainer = Trainer(env=env, checkpoint_dir=str(tmp_path), total_generations=1)
    trainer._model = trainer._build_model()
    result = trainer._evaluate(trainer._model, n_eval_episodes=2)
    assert "action_counts" in result
    ac = result["action_counts"]
    assert "buy" in ac and "hold" in ac and "sell" in ac
    total_steps = ac["buy"] + ac["hold"] + ac["sell"]
    assert total_steps > 0


def test_evaluate_returns_price_and_action_series(tmp_path):
    from env.crypto_env import CryptoEnv
    from agent.trainer import Trainer
    env = CryptoEnv(data=make_mock_data(), window_size=60, episode_length=50)
    trainer = Trainer(env=env, checkpoint_dir=str(tmp_path), total_generations=1)
    trainer._model = trainer._build_model()
    result = trainer._evaluate(trainer._model, n_eval_episodes=1)
    assert "price_series" in result
    assert "action_series" in result
    assert len(result["price_series"]) == len(result["action_series"])
    assert len(result["price_series"]) > 0


def test_notify_payload_includes_action_metrics(tmp_path, mocker):
    from queue import Queue
    from env.crypto_env import CryptoEnv
    from agent.trainer import Trainer
    env = CryptoEnv(data=make_mock_data(), window_size=60, episode_length=50)
    queue = Queue()
    trainer = Trainer(
        env=env,
        checkpoint_dir=str(tmp_path),
        total_generations=1,
        n_steps=64,
        batch_size=32,
        update_queue=queue,
    )
    mocker.patch.object(trainer, "_evaluate", return_value={
        "sharpe": 0.5,
        "final_balance": 10000.0,
        "pnl": 0.0,
        "initial_balance": 10000.0,
        "win_rate": 0.8,
        "action_counts": {"buy": 10, "hold": 80, "sell": 10},
        "price_series": [100.0, 101.0],
        "action_series": [0, 1],
    })
    trainer.run()
    payload = queue.get()
    assert "win_rate" in payload
    assert "action_counts" in payload
    assert "cumulative_buys" in payload
    assert "cumulative_sells" in payload


def test_cumulative_buys_sells_increment_across_generations(tmp_path, mocker):
    from queue import Queue
    from env.crypto_env import CryptoEnv
    from agent.trainer import Trainer
    env = CryptoEnv(data=make_mock_data(), window_size=60, episode_length=50)
    queue = Queue()
    trainer = Trainer(
        env=env,
        checkpoint_dir=str(tmp_path),
        total_generations=2,
        n_steps=64,
        batch_size=32,
        update_queue=queue,
    )
    eval_result = {
        "sharpe": 0.5,
        "final_balance": 10000.0,
        "pnl": 0.0,
        "initial_balance": 10000.0,
        "win_rate": 0.5,
        "action_counts": {"buy": 5, "hold": 40, "sell": 5},
        "price_series": [100.0],
        "action_series": [0],
    }
    mocker.patch.object(trainer, "_evaluate", return_value=eval_result)
    trainer.run()
    payloads = [queue.get() for _ in range(2)]
    assert payloads[0]["cumulative_buys"] == 5
    assert payloads[1]["cumulative_buys"] == 10
    assert payloads[0]["cumulative_sells"] == 5
    assert payloads[1]["cumulative_sells"] == 10
