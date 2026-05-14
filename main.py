import argparse
import signal
import threading
from pathlib import Path
from queue import Queue

import yaml
from dotenv import load_dotenv

from logger import logger


def load_config(path: str = "config.yaml") -> dict:
    with open(path, "r") as f:
        return yaml.safe_load(f)


def build_trainer(config: dict, env, queue: Queue, checkpoint_dir: str, resume: bool = True):
    from agent.trainer import Trainer
    return Trainer(
        env=env,
        checkpoint_dir=checkpoint_dir,
        total_generations=config["agent"]["total_episodes"],
        learning_rate=config["agent"]["learning_rate"],
        n_steps=config["agent"]["n_steps"],
        batch_size=config["agent"]["batch_size"],
        clip_range=config["agent"]["clip_range"],
        promote_threshold=config["agent"]["promote_threshold"],
        checkpoint_interval=config["self_play"]["checkpoint_interval"],
        update_queue=queue,
        wandb_project=config["logging"]["project_name"] if config["logging"]["wandb"] else None,
        resume=resume,
    )


def build_env(config: dict, data):
    from env.crypto_env import CryptoEnv
    return CryptoEnv(
        data=data,
        window_size=config["data"]["window_size"],
        initial_balance=config["env"]["initial_balance"],
        transaction_cost=config["env"]["transaction_cost"],
        episode_length=config["env"]["episode_length"],
    )


def fetch_data(config: dict):
    from data.fetcher import fetch_ohlcv, load_cache, cache_ohlcv
    cache_path = f"data/cache/{config['data']['symbol'].replace('/', '_')}_{config['data']['timeframe']}.parquet"
    Path(cache_path).parent.mkdir(parents=True, exist_ok=True)
    if Path(cache_path).exists():
        logger.info(f"Loading cached data from {cache_path}")
        return load_cache(cache_path)
    logger.info(f"Fetching OHLCV from {config['data']['exchange']}...")
    df = fetch_ohlcv(
        config["data"]["exchange"],
        config["data"]["symbol"],
        config["data"]["timeframe"],
        limit=2000,
    )
    cache_ohlcv(df, cache_path)
    logger.info(f"Cached {len(df)} candles to {cache_path}")
    return df


def main() -> None:
    parser = argparse.ArgumentParser(description="TradingZero training")
    parser.add_argument(
        "--no-resume",
        action="store_true",
        help="Start training from scratch, ignoring existing checkpoints",
    )
    args = parser.parse_args()

    load_dotenv()
    config = load_config()
    logger.info("TradingZero starting up")
    logger.info(f"Exchange: {config['data']['exchange']} | Symbol: {config['data']['symbol']}")
    logger.info(f"Resume: {not args.no_resume}")

    data = fetch_data(config)
    env = build_env(config, data)

    queue: Queue = Queue()
    checkpoint_dir = config["self_play"]["checkpoint_dir"]
    trainer = build_trainer(config, env, queue, checkpoint_dir, resume=not args.no_resume)

    def handle_shutdown(signum, frame):
        logger.info("Shutdown signal received — stopping trainer...")
        trainer.stop()

    signal.signal(signal.SIGINT, handle_shutdown)
    signal.signal(signal.SIGTERM, handle_shutdown)

    from tui.app import TUIApp
    app = TUIApp(update_queue=queue)

    training_thread = threading.Thread(target=trainer.run, daemon=True)
    training_thread.start()
    logger.info("Training thread started")

    try:
        app.run()
    finally:
        trainer.stop()
        training_thread.join(timeout=10)
        logger.info("TradingZero shutdown complete")


if __name__ == "__main__":
    main()
