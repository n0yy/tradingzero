from __future__ import annotations

from types import SimpleNamespace

import pandas as pd


def make_market_data(count: int = 2000) -> pd.DataFrame:
    rows = [
        [1700000000000 + i * 900_000, 30_000 + i, 30_050 + i, 29_950 + i, 30_010 + i, 100 + i]
        for i in range(count)
    ]
    return pd.DataFrame(rows, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])


def make_config() -> dict:
    return {
        'data': {
            'exchange': 'binance',
            'symbol': 'BTC/USDT',
            'timeframe': '15m',
            'window_size': 60,
        },
        'env': {
            'initial_balance': 10_000,
            'transaction_cost': 0.001,
            'episode_length': 500,
        },
        'agent': {
            'learning_rate': 1e-4,
            'n_steps': 256,
            'batch_size': 64,
            'clip_range': 0.2,
            'total_episodes': 10,
            'promote_threshold': 0.05,
        },
        'self_play': {
            'checkpoint_interval': 5,
            'checkpoint_dir': 'agent/checkpoints',
        },
        'logging': {
            'wandb': False,
            'project_name': 'tradingzero-test',
        },
    }


def test_build_run_evaluation_plan_splits_chronological_holdout():
    from backend.evaluation_spec import build_run_evaluation_plan

    data = make_market_data()
    plan = build_run_evaluation_plan(
        config=make_config(),
        data=data,
        training_seed=111,
        evaluation_seed=222,
    )

    spec = plan.evaluation_spec
    assert len(plan.training_data) < len(data)
    assert len(plan.evaluation_data) < len(data)
    assert spec['training_slice']['start_index'] == 0
    assert spec['training_slice']['end_index'] < spec['evaluation_slice']['start_index']
    assert spec['evaluation_slice']['end_index'] == len(data) - 1
    assert spec['training_seed'] == 111
    assert spec['evaluation_seed'] == 222


def test_build_run_evaluation_plan_generates_stable_evenly_spaced_anchors():
    from backend.evaluation_spec import build_run_evaluation_plan

    data = make_market_data()
    plan_a = build_run_evaluation_plan(
        config=make_config(),
        data=data,
        training_seed=111,
        evaluation_seed=222,
    )
    plan_b = build_run_evaluation_plan(
        config=make_config(),
        data=data,
        training_seed=111,
        evaluation_seed=222,
    )

    anchors_a = plan_a.evaluation_spec['evaluation_anchors']
    anchors_b = plan_b.evaluation_spec['evaluation_anchors']

    assert anchors_a == anchors_b
    assert [anchor['label'] for anchor in anchors_a] == ['A1', 'A2', 'A3', 'A4']

    anchor_indices = [anchor['start_index'] for anchor in anchors_a]
    assert anchor_indices == sorted(anchor_indices)

    gaps = [curr - prev for prev, curr in zip(anchor_indices, anchor_indices[1:])]
    assert max(gaps) - min(gaps) <= 1


def test_build_trainer_runtime_uses_training_slice_for_env(mocker):
    from backend.evaluation_spec import build_run_evaluation_plan
    from backend.training_runtime import build_trainer_runtime

    config = make_config()
    data = make_market_data()
    plan = build_run_evaluation_plan(
        config=config,
        data=data,
        training_seed=111,
        evaluation_seed=222,
    )

    mocker.patch('backend.training_runtime.load_config', return_value=config)
    mocker.patch('backend.training_runtime.load_dotenv')
    build_env = mocker.patch('backend.training_runtime.build_env', return_value='env')
    build_trainer = mocker.patch(
        'backend.training_runtime.build_trainer',
        return_value=SimpleNamespace(update_queue='queue'),
    )

    trainer = build_trainer_runtime(config_path='config.yaml', evaluation_plan=plan)

    assert build_env.call_count == 1
    assert len(build_env.call_args.args[1]) == len(plan.training_data)
    assert len(build_env.call_args.args[1]) < len(data)
    assert trainer.evaluation_spec == plan.evaluation_spec
    assert len(trainer.evaluation_data) == len(plan.evaluation_data)
    assert build_trainer.call_count == 1
