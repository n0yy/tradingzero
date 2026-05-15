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
    mocker.patch.object(
        trainer,
        "_evaluate",
        side_effect=[
            {
                "sharpe": 1.0,
                "final_balance": 10000.0,
                "pnl": 0.0,
                "initial_balance": 10000.0,
                "executed_trade_count": 6,
                "sell_realized_exit_count": 3,
            },
            {
                "sharpe": 2.0,
                "final_balance": 10000.0,
                "pnl": 0.0,
                "initial_balance": 10000.0,
                "executed_trade_count": 8,
                "sell_realized_exit_count": 4,
            },
        ],
    )
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
    trainer = Trainer(
        env=env,
        checkpoint_dir=str(tmp_path),
        total_generations=2,
        promote_threshold=0.5,
        n_steps=64,
        batch_size=32,
    )
    mocker.patch.object(
        trainer,
        "_evaluate",
        side_effect=[
            {
                "sharpe": 0.1,
                "final_balance": 10000.0,
                "pnl": 0.0,
                "initial_balance": 10000.0,
                "executed_trade_count": 6,
                "sell_realized_exit_count": 3,
            },
            {
                "sharpe": 0.15,
                "final_balance": 10000.0,
                "pnl": 0.0,
                "initial_balance": 10000.0,
                "executed_trade_count": 6,
                "sell_realized_exit_count": 3,
            },
        ],
    )
    trainer.run()
    assert not (tmp_path / "best.zip").exists()


def test_promotion_does_not_trigger_when_activity_evidence_is_too_low(tmp_path, mocker):
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
    mocker.patch.object(
        trainer,
        "_evaluate",
        side_effect=[
            {
                "sharpe": 1.0,
                "final_balance": 10000.0,
                "pnl": 0.0,
                "initial_balance": 10000.0,
                "executed_trade_count": 6,
                "sell_realized_exit_count": 3,
            },
            {
                "sharpe": 2.0,
                "final_balance": 10000.0,
                "pnl": 0.0,
                "initial_balance": 10000.0,
                "executed_trade_count": 1,
                "sell_realized_exit_count": 0,
            },
        ],
    )
    trainer.run()
    assert trainer.best_sharpe == 1.0
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
    mocker.patch.object(
        trainer,
        "_evaluate",
        return_value={
            "sharpe": 0.1,
            "final_balance": 10000.0,
            "pnl": 0.0,
            "initial_balance": 10000.0,
            "executed_trade_count": 6,
            "sell_realized_exit_count": 3,
        },
    )
    trainer.run()
    payloads = []
    while not queue.empty():
        payloads.append(queue.get())
    generation_payloads = [payload for payload in payloads if payload.get("kind") != "step_batch"]
    assert len(generation_payloads) == 2
    payload = generation_payloads[0]
    assert "generation" in payload
    assert "training_sharpe" in payload
    assert "evaluation_sharpe" in payload
    assert "best_evaluation_sharpe" in payload
    assert "evaluation_executed_trade_count" in payload
    assert "evaluation_sell_realized_exit_count" in payload
    assert "promotion_gate_checks" in payload
    assert "promotion_gate_reasons" in payload
    assert "anchor_results" in payload
    assert any(payload.get("kind") == "step_batch" for payload in payloads)


def test_promotion_payload_reports_activity_gate_failures(tmp_path, mocker):
    from queue import Queue
    from env.crypto_env import CryptoEnv
    from agent.trainer import Trainer

    env = CryptoEnv(data=make_mock_data(), window_size=60, episode_length=50)
    queue = Queue()
    trainer = Trainer(
        env=env,
        checkpoint_dir=str(tmp_path),
        total_generations=2,
        promote_threshold=0.05,
        n_steps=64,
        batch_size=32,
        update_queue=queue,
    )
    mocker.patch.object(
        trainer,
        "_evaluate",
        side_effect=[
            {
                "sharpe": 1.0,
                "final_balance": 10000.0,
                "pnl": 0.0,
                "initial_balance": 10000.0,
                "executed_trade_count": 6,
                "sell_realized_exit_count": 3,
            },
            {
                "sharpe": 1.5,
                "final_balance": 10000.0,
                "pnl": 0.0,
                "initial_balance": 10000.0,
                "executed_trade_count": 1,
                "sell_realized_exit_count": 0,
            },
        ],
    )
    trainer.run()

    generation_payloads = []
    while not queue.empty():
        candidate = queue.get()
        if candidate.get("kind") != "step_batch":
            generation_payloads.append(candidate)

    final_payload = generation_payloads[-1]
    assert final_payload["promoted"] is False
    assert final_payload["evaluation_executed_trade_count"] == 1
    assert final_payload["evaluation_sell_realized_exit_count"] == 0
    assert any("Executed Trade count 1 was below minimum" in reason for reason in final_payload["promotion_gate_reasons"])
    assert any("SELL realized exits 0 were below minimum" in reason for reason in final_payload["promotion_gate_reasons"])


def test_promotion_logs_decision_and_gate_reasons(tmp_path, mocker):
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
    mock_logger = mocker.patch("agent.trainer.logger")
    mocker.patch.object(
        trainer,
        "_evaluate",
        side_effect=[
            {
                "sharpe": 1.0,
                "final_balance": 10000.0,
                "pnl": 0.0,
                "initial_balance": 10000.0,
                "executed_trade_count": 6,
                "sell_realized_exit_count": 3,
            },
            {
                "sharpe": 1.5,
                "final_balance": 10000.0,
                "pnl": 0.0,
                "initial_balance": 10000.0,
                "executed_trade_count": 1,
                "sell_realized_exit_count": 0,
            },
        ],
    )
    trainer.run()

    logged_messages = [" ".join(str(arg) for arg in call.args) for call in mock_logger.info.call_args_list]
    assert any("Gate [FAIL] executed_trade_count" in message for message in logged_messages)
    assert any("Promotion decision: NOT PROMOTED" in message for message in logged_messages)


# --- Issue #10: action metrics & trade win rate ---

def test_evaluate_does_not_return_episode_win_rate(tmp_path):
    from env.crypto_env import CryptoEnv
    from agent.trainer import Trainer
    env = CryptoEnv(data=make_mock_data(), window_size=60, episode_length=50)
    trainer = Trainer(env=env, checkpoint_dir=str(tmp_path), total_generations=1)
    trainer._model = trainer._build_model()
    result = trainer._evaluate(trainer._model, n_eval_episodes=2)
    assert "win_rate" not in result


def test_evaluate_returns_action_counts(tmp_path):
    from env.crypto_env import CryptoEnv
    from agent.trainer import Trainer
    env = CryptoEnv(data=make_mock_data(), window_size=60, episode_length=50)
    trainer = Trainer(env=env, checkpoint_dir=str(tmp_path), total_generations=1)
    trainer._model = trainer._build_model()
    result = trainer._evaluate(trainer._model, n_eval_episodes=2)
    assert "transaction_distribution" in result
    ac = result["transaction_distribution"]
    assert "buy" in ac and "sell" in ac and "no_transaction" in ac
    total_steps = ac["buy"] + ac["sell"] + ac["no_transaction"]
    assert total_steps > 0


def test_evaluate_returns_price_and_action_series(tmp_path):
    from env.crypto_env import CryptoEnv
    from agent.trainer import Trainer
    env = CryptoEnv(data=make_mock_data(), window_size=60, episode_length=50)
    trainer = Trainer(env=env, checkpoint_dir=str(tmp_path), total_generations=1)
    trainer._model = trainer._build_model()
    result = trainer._evaluate(trainer._model, n_eval_episodes=1)
    assert "price_series" in result
    assert "transaction_outcome_series" in result
    assert len(result["price_series"]) == len(result["transaction_outcome_series"])
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
        "transaction_distribution": {"buy": 10, "sell": 10, "no_transaction": 80},
        "price_series": [100.0, 101.0],
        "transaction_outcome_series": [0, 1],
    })
    trainer.run()
    payload = None
    while not queue.empty():
        candidate = queue.get()
        if candidate.get("kind") != "step_batch":
            payload = candidate
            break
    assert payload is not None
    assert "trade_win_rate" in payload
    assert "transaction_distribution" in payload
    assert "action_counts" in payload
    assert "cumulative_buys" in payload
    assert "cumulative_sells" in payload


def test_cumulative_buys_sells_increment_with_executed_trades(tmp_path):
    from queue import Queue
    from env.crypto_env import CryptoEnv
    from agent.trainer import Trainer
    env = CryptoEnv(data=make_mock_data(), window_size=60, episode_length=50)
    queue = Queue()
    trainer = Trainer(env=env, checkpoint_dir=str(tmp_path), total_generations=2, update_queue=queue)

    trainer._notify_step(
        generation=1,
        action=np.array([1, 0]),
        reward=0.1,
        info={
            "price": 100.0,
            "balance": 10010.0,
            "position": 0.25,
            "position_before": 0.0,
            "position_after": 0.25,
            "executed_delta": 0.25,
            "requested_direction": "BUY",
            "requested_size_percent": 0.25,
            "transaction_outcome": "BUY",
            "is_transaction": True,
            "cost": 0.001,
            "timestamp": "2026-05-15T00:00:00Z",
            "executed_trade": {
                "action": "BUY",
                "timestamp": "2026-05-15T00:00:00Z",
                "execution_price": 100.0,
                "size_percent": 0.25,
                "position_before": 0.0,
                "position_after": 0.25,
                "notional_usd": 2500.0,
                "balance_before": 10000.0,
                "balance_after": 10010.0,
                "fee": 10.0,
                "realized_pnl": 0.0,
                "unrealized_pnl_after": 0.0,
            },
        },
    )
    trainer._notify_step(
        generation=1,
        action=np.array([2, 0]),
        reward=0.1,
        info={
            "price": 101.0,
            "balance": 10020.0,
            "position": 0.0,
            "position_before": 0.25,
            "position_after": 0.0,
            "executed_delta": -0.25,
            "requested_direction": "SELL",
            "requested_size_percent": 0.25,
            "transaction_outcome": "SELL",
            "is_transaction": True,
            "cost": 0.001,
            "timestamp": "2026-05-15T00:15:00Z",
            "executed_trade": {
                "action": "SELL",
                "timestamp": "2026-05-15T00:15:00Z",
                "execution_price": 101.0,
                "size_percent": 0.25,
                "position_before": 0.25,
                "position_after": 0.0,
                "notional_usd": 2502.5,
                "balance_before": 10010.0,
                "balance_after": 10020.0,
                "fee": 10.01,
                "realized_pnl": 12.5,
                "unrealized_pnl_after": 0.0,
            },
        },
    )

    payloads = [queue.get(), queue.get()]
    assert payloads[0]["cumulative_buys"] == 1
    assert payloads[0]["cumulative_sells"] == 0
    assert payloads[1]["cumulative_buys"] == 1
    assert payloads[1]["cumulative_sells"] == 1
    assert payloads[1]["trade_win_rate"] == 1.0
    assert payloads[1]["winning_trades"] == 1
    assert payloads[1]["losing_trades"] == 0


def test_trainer_step_stream_payload_contains_live_fields(tmp_path):
    from queue import Queue
    from env.crypto_env import CryptoEnv
    from agent.trainer import Trainer
    env = CryptoEnv(data=make_mock_data(), window_size=60, episode_length=50)
    queue = Queue()
    trainer = Trainer(env=env, checkpoint_dir=str(tmp_path), total_generations=1, update_queue=queue)

    trainer._notify_step(
        generation=1,
        action=np.array([1, 2]),
        reward=0.25,
        info={
            "price": 30100.0,
            "position": 0.75,
            "position_before": 0.0,
            "position_after": 0.75,
            "executed_delta": 0.75,
            "balance": 10100.0,
            "requested_direction": "BUY",
            "requested_size_percent": 0.75,
            "transaction_outcome": "BUY",
            "is_transaction": True,
            "cost": 0.001,
            "timestamp": "2026-05-15T00:00:00Z",
            "executed_trade": {
                "action": "BUY",
                "timestamp": "2026-05-15T00:00:00Z",
                "execution_price": 30100.0,
                "size_percent": 0.75,
                "position_before": 0.0,
                "position_after": 0.75,
                "notional_usd": 7500.0,
                "balance_before": 10000.0,
                "balance_after": 10100.0,
                "fee": 10.0,
                "realized_pnl": 0.0,
                "unrealized_pnl_after": 0.0,
            },
        },
    )

    payload = queue.get()
    assert payload["kind"] == "step_batch"
    assert payload["generation"] == 1
    assert payload["price"] == 30100.0
    assert payload["requested_direction"] == "BUY"
    assert payload["transaction_outcome"] == "BUY"
    assert payload["is_transaction"] is True
    assert payload["position"] == 0.75
    assert payload["balance"] == 10100.0
    assert payload["pnl"] == 100.0
    assert payload["rolling_reward"] == 0.25
    assert payload["equity_curve"][-1] == 10100.0
    assert payload["cumulative_buys"] == 1
    assert payload["trade_win_rate"] == 0.0
    assert payload["executed_trade"]["action"] == "BUY"


def test_evaluate_returns_neutral_payload_when_stop_requested(tmp_path):
    from env.crypto_env import CryptoEnv
    from agent.trainer import Trainer
    env = CryptoEnv(data=make_mock_data(), window_size=60, episode_length=50)
    trainer = Trainer(env=env, checkpoint_dir=str(tmp_path), total_generations=1)

    trainer.stop()
    result = trainer._evaluate(trainer._build_model(), n_eval_episodes=2)

    assert result["sharpe"] == 0.0
    assert result["final_balance"] == env.initial_balance
    assert result["pnl"] == 0.0
    assert "win_rate" not in result
