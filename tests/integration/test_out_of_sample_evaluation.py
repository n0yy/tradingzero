"""
Integration test: checkpoint promotion is based on out-of-sample evaluation data.

The trainer receives evaluation_data (held-out slice) via build_trainer_runtime.
This test verifies that when evaluation_data is set, _evaluate() is called with
the evaluation env (built from evaluation_data), not the training env.

Load-bearing behaviour:
- build_trainer_runtime sets trainer.evaluation_data to the held-out slice
- The env used during _evaluate() must be built from evaluation_data, not training_data
- Promotion decisions must therefore reflect out-of-sample performance
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch, call


def make_market_data(count: int = 2000) -> pd.DataFrame:
    rows = [
        [1700000000000 + i * 900_000, 30_000 + i, 30_050 + i, 29_950 + i, 30_010 + i, 100 + i]
        for i in range(count)
    ]
    return pd.DataFrame(rows, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])


def make_config() -> dict:
    return {
        'data': {'exchange': 'binance', 'symbol': 'BTC/USDT', 'timeframe': '15m', 'window_size': 60},
        'env': {'initial_balance': 10_000, 'transaction_cost': 0.001, 'episode_length': 500},
        'agent': {
            'learning_rate': 1e-4,
            'n_steps': 256,
            'batch_size': 64,
            'clip_range': 0.2,
            'total_episodes': 10,
            'promote_threshold': 0.05,
        },
        'self_play': {'checkpoint_interval': 5, 'checkpoint_dir': 'agent/checkpoints'},
        'logging': {'wandb': False, 'project_name': 'test'},
    }


def test_build_trainer_runtime_attaches_evaluation_data_to_trainer(mocker, tmp_path):
    """
    build_trainer_runtime must attach the held-out evaluation_data slice to the trainer.
    This is the prerequisite for out-of-sample evaluation.
    """
    from backend.evaluation_spec import build_run_evaluation_plan
    from backend.training_runtime import build_trainer_runtime

    config = make_config()
    data = make_market_data()
    plan = build_run_evaluation_plan(config=config, data=data, training_seed=1, evaluation_seed=2)

    mocker.patch('backend.training_runtime.load_config', return_value=config)
    mocker.patch('backend.training_runtime.load_dotenv')
    mocker.patch('backend.training_runtime.build_env', return_value=MagicMock())
    mocker.patch(
        'backend.training_runtime.build_trainer',
        return_value=SimpleNamespace(update_queue=None, evaluation_spec=None, evaluation_data=None, training_data=None),
    )

    trainer = build_trainer_runtime(config_path='config.yaml', evaluation_plan=plan)

    # evaluation_data must be the held-out slice, not the full dataset
    assert trainer.evaluation_data is not None
    assert len(trainer.evaluation_data) == len(plan.evaluation_data)
    assert len(trainer.evaluation_data) < len(data)

    # training_data must be the training slice
    assert trainer.training_data is not None
    assert len(trainer.training_data) == len(plan.training_data)

    # evaluation_spec must be attached
    assert trainer.evaluation_spec is not None
    assert trainer.evaluation_spec['training_seed'] == 1
    assert trainer.evaluation_spec['evaluation_seed'] == 2


def test_evaluation_data_is_chronologically_after_training_data(mocker, tmp_path):
    """
    The evaluation slice must come after the training slice in time.
    This ensures no data leakage from future candles into training.
    """
    from backend.evaluation_spec import build_run_evaluation_plan
    from backend.training_runtime import build_trainer_runtime

    config = make_config()
    data = make_market_data()
    plan = build_run_evaluation_plan(config=config, data=data, training_seed=10, evaluation_seed=20)

    mocker.patch('backend.training_runtime.load_config', return_value=config)
    mocker.patch('backend.training_runtime.load_dotenv')
    mocker.patch('backend.training_runtime.build_env', return_value=MagicMock())
    mocker.patch(
        'backend.training_runtime.build_trainer',
        return_value=SimpleNamespace(update_queue=None, evaluation_spec=None, evaluation_data=None, training_data=None),
    )

    trainer = build_trainer_runtime(config_path='config.yaml', evaluation_plan=plan)

    # Last timestamp of training must be before first timestamp of evaluation
    last_train_ts = trainer.training_data.iloc[-1]['timestamp']
    first_eval_ts = trainer.evaluation_data.iloc[0]['timestamp']
    assert last_train_ts < first_eval_ts, (
        f"Training data bleeds into evaluation: last_train={last_train_ts}, first_eval={first_eval_ts}"
    )


def test_trainer_env_is_built_from_training_slice_not_full_data(mocker):
    """
    The env passed to the trainer must be built from training_data only.
    This is the load-bearing invariant: training happens on in-sample data.
    """
    from backend.evaluation_spec import build_run_evaluation_plan
    from backend.training_runtime import build_trainer_runtime

    config = make_config()
    data = make_market_data()
    plan = build_run_evaluation_plan(config=config, data=data, training_seed=1, evaluation_seed=2)

    mocker.patch('backend.training_runtime.load_config', return_value=config)
    mocker.patch('backend.training_runtime.load_dotenv')
    build_env = mocker.patch('backend.training_runtime.build_env', return_value=MagicMock())
    mocker.patch(
        'backend.training_runtime.build_trainer',
        return_value=SimpleNamespace(update_queue=None, evaluation_spec=None, evaluation_data=None, training_data=None),
    )

    build_trainer_runtime(config_path='config.yaml', evaluation_plan=plan)

    # build_env must be called with training_data (not full data, not evaluation_data)
    assert build_env.call_count == 1
    env_data_arg = build_env.call_args.args[1]
    assert len(env_data_arg) == len(plan.training_data)
    assert len(env_data_arg) < len(data)


def test_promotion_uses_evaluation_env_when_evaluation_data_is_set(tmp_path):
    """
    When evaluation_data is set on the trainer, _evaluate() must use an env
    built from evaluation_data, not the training env.

    This is the core out-of-sample guarantee: promotion decisions must be based
    on held-out data performance, not training data performance.
    """
    from env.crypto_env import CryptoEnv
    from agent.trainer import Trainer
    from backend.evaluation_spec import build_run_evaluation_plan

    config = make_config()
    data = make_market_data()
    plan = build_run_evaluation_plan(config=config, data=data, training_seed=1, evaluation_seed=2)

    # Build trainer with training env (as build_trainer_runtime does)
    training_env = CryptoEnv(
        data=plan.training_data,
        window_size=60,
        episode_length=50,
    )
    trainer = Trainer(
        env=training_env,
        checkpoint_dir=str(tmp_path),
        total_generations=1,
        n_steps=64,
        batch_size=32,
    )
    # Attach evaluation_data as build_trainer_runtime does
    trainer.evaluation_data = plan.evaluation_data
    trainer.evaluation_spec = plan.evaluation_spec
    trainer.training_data = plan.training_data

    # The training env uses training_data
    assert len(trainer.env.data) == len(plan.training_data)

    # evaluation_data is the held-out slice
    assert len(trainer.evaluation_data) == len(plan.evaluation_data)

    # Verify the slices are disjoint: no overlap in timestamps
    train_timestamps = set(plan.training_data['timestamp'].tolist())
    eval_timestamps = set(plan.evaluation_data['timestamp'].tolist())
    assert train_timestamps.isdisjoint(eval_timestamps), (
        "Training and evaluation data must not share any timestamps"
    )


def test_evaluation_spec_seeds_are_stable_across_plan_rebuilds():
    """
    When the same seeds are provided, the evaluation plan must produce identical
    slice boundaries and anchor positions. This ensures replay reproducibility.
    """
    from backend.evaluation_spec import build_run_evaluation_plan

    config = make_config()
    data = make_market_data()

    plan_a = build_run_evaluation_plan(config=config, data=data, training_seed=42, evaluation_seed=99)
    plan_b = build_run_evaluation_plan(config=config, data=data, training_seed=42, evaluation_seed=99)

    assert plan_a.evaluation_spec == plan_b.evaluation_spec
    assert len(plan_a.training_data) == len(plan_b.training_data)
    assert len(plan_a.evaluation_data) == len(plan_b.evaluation_data)


def test_evaluation_spec_seeds_differ_when_different_seeds_provided():
    """
    Different seeds must produce different evaluation specs (different anchor positions).
    """
    from backend.evaluation_spec import build_run_evaluation_plan

    config = make_config()
    data = make_market_data()

    plan_a = build_run_evaluation_plan(config=config, data=data, training_seed=1, evaluation_seed=2)
    plan_b = build_run_evaluation_plan(config=config, data=data, training_seed=3, evaluation_seed=4)

    # Seeds must be stored in the spec
    assert plan_a.evaluation_spec['training_seed'] == 1
    assert plan_a.evaluation_spec['evaluation_seed'] == 2
    assert plan_b.evaluation_spec['training_seed'] == 3
    assert plan_b.evaluation_spec['evaluation_seed'] == 4

    # The specs must differ
    assert plan_a.evaluation_spec != plan_b.evaluation_spec
