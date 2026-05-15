from __future__ import annotations

from pathlib import Path
from queue import Queue

import yaml
from dotenv import load_dotenv

from backend.evaluation_spec import RunEvaluationPlan, build_run_evaluation_plan
from logger import logger


def load_config(path: str = 'config.yaml') -> dict:
    with open(path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def fetch_data(config: dict):
    from data.fetcher import cache_ohlcv, fetch_ohlcv, load_cache

    cache_path = f"data/cache/{config['data']['symbol'].replace('/', '_')}_{config['data']['timeframe']}.parquet"
    Path(cache_path).parent.mkdir(parents=True, exist_ok=True)
    if Path(cache_path).exists():
        logger.info(f'Loading cached data from {cache_path}')
        return load_cache(cache_path)

    logger.info(f"Fetching OHLCV from {config['data']['exchange']}...")
    df = fetch_ohlcv(
        config['data']['exchange'],
        config['data']['symbol'],
        config['data']['timeframe'],
        limit=2000,
    )
    cache_ohlcv(df, cache_path)
    logger.info(f'Cached {len(df)} candles to {cache_path}')
    return df


def build_env(config: dict, data):
    from env.crypto_env import CryptoEnv

    return CryptoEnv(
        data=data,
        window_size=config['data']['window_size'],
        initial_balance=config['env']['initial_balance'],
        transaction_cost=config['env']['transaction_cost'],
        episode_length=config['env']['episode_length'],
    )


def build_trainer(
    config: dict,
    env,
    queue: Queue,
    checkpoint_dir: str,
    resume: bool = True,
    resume_from: str | None = None,
):
    from agent.trainer import Trainer

    return Trainer(
        env=env,
        checkpoint_dir=checkpoint_dir,
        total_generations=config['agent']['total_episodes'],
        learning_rate=config['agent']['learning_rate'],
        n_steps=config['agent']['n_steps'],
        batch_size=config['agent']['batch_size'],
        clip_range=config['agent']['clip_range'],
        promote_threshold=config['agent']['promote_threshold'],
        checkpoint_interval=config['self_play']['checkpoint_interval'],
        update_queue=queue,
        wandb_project=config['logging']['project_name'] if config['logging']['wandb'] else None,
        resume=resume,
        resume_from=resume_from,
    )


def build_trainer_runtime(
    config_path: str = 'config.yaml',
    resume: bool = True,
    resume_from: str | None = None,
    evaluation_plan: RunEvaluationPlan | None = None,
):
    load_dotenv()
    config = load_config(config_path)
    plan = evaluation_plan
    if plan is None:
        data = fetch_data(config)
        plan = build_run_evaluation_plan(config=config, data=data)
    env = build_env(config, plan.training_data)
    queue: Queue = Queue()
    checkpoint_dir = config['self_play']['checkpoint_dir']
    trainer = build_trainer(config, env, queue, checkpoint_dir, resume=resume, resume_from=resume_from)
    trainer.evaluation_spec = plan.evaluation_spec
    trainer.evaluation_data = plan.evaluation_data
    trainer.training_data = plan.training_data
    return trainer
