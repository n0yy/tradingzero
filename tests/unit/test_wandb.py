import numpy as np
import pandas as pd
import pytest


def make_mock_data(n=700):
    rows = [
        [1700000000000 + i * 3600000, 30000 + i, 30100 + i, 29900 + i, 30050 + i, 100 + i]
        for i in range(n)
    ]
    return pd.DataFrame(rows, columns=["timestamp", "open", "high", "low", "close", "volume"])


# --- Tracer bullet: wandb.init called on run ---

def test_wandb_init_called_on_run(tmp_path, mocker):
    from env.crypto_env import CryptoEnv
    from agent.trainer import Trainer

    mock_wandb = mocker.patch("agent.trainer.wandb")
    mock_wandb.init.return_value = MagicMock()

    env = CryptoEnv(data=make_mock_data(), window_size=60, episode_length=50)
    trainer = Trainer(
        env=env,
        checkpoint_dir=str(tmp_path),
        total_generations=1,
        n_steps=64,
        batch_size=32,
        wandb_project="test_project",
    )
    mocker.patch.object(trainer, "_evaluate", return_value={"sharpe": 0.1, "final_balance": 10000.0, "pnl": 0.0, "initial_balance": 10000.0})
    trainer.run()

    mock_wandb.init.assert_called_once()
    call_kwargs = mock_wandb.init.call_args.kwargs
    assert call_kwargs.get("project") == "test_project"


from unittest.mock import MagicMock


def test_wandb_log_called_per_generation(tmp_path, mocker):
    from env.crypto_env import CryptoEnv
    from agent.trainer import Trainer

    mock_wandb = mocker.patch("agent.trainer.wandb")
    env = CryptoEnv(data=make_mock_data(), window_size=60, episode_length=50)
    trainer = Trainer(
        env=env,
        checkpoint_dir=str(tmp_path),
        total_generations=3,
        n_steps=64,
        batch_size=32,
        wandb_project="test_project",
    )
    mocker.patch.object(trainer, "_evaluate", return_value={"sharpe": 0.1, "final_balance": 10000.0, "pnl": 0.0, "initial_balance": 10000.0})
    trainer.run()

    assert mock_wandb.log.call_count == 3
    logged = mock_wandb.log.call_args_list[0].args[0]
    assert "generation" in logged
    assert "current_sharpe" in logged
    assert "best_sharpe" in logged
    assert "promoted" in logged


def test_wandb_finish_called_after_run(tmp_path, mocker):
    from env.crypto_env import CryptoEnv
    from agent.trainer import Trainer

    mock_wandb = mocker.patch("agent.trainer.wandb")
    env = CryptoEnv(data=make_mock_data(), window_size=60, episode_length=50)
    trainer = Trainer(
        env=env,
        checkpoint_dir=str(tmp_path),
        total_generations=1,
        n_steps=64,
        batch_size=32,
        wandb_project="test_project",
    )
    mocker.patch.object(trainer, "_evaluate", return_value={"sharpe": 0.1, "final_balance": 10000.0, "pnl": 0.0, "initial_balance": 10000.0})
    trainer.run()

    mock_wandb.finish.assert_called_once()


def test_wandb_disabled_when_no_project(tmp_path, mocker):
    from env.crypto_env import CryptoEnv
    from agent.trainer import Trainer

    mock_wandb = mocker.patch("agent.trainer.wandb")
    env = CryptoEnv(data=make_mock_data(), window_size=60, episode_length=50)
    trainer = Trainer(
        env=env,
        checkpoint_dir=str(tmp_path),
        total_generations=1,
        n_steps=64,
        batch_size=32,
        wandb_project=None,
    )
    mocker.patch.object(trainer, "_evaluate", return_value={"sharpe": 0.1, "final_balance": 10000.0, "pnl": 0.0, "initial_balance": 10000.0})
    trainer.run()

    mock_wandb.init.assert_not_called()
    mock_wandb.log.assert_not_called()
    mock_wandb.finish.assert_not_called()
