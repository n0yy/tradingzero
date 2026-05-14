import numpy as np
import pandas as pd
from pathlib import Path


def make_mock_data(n=700):
    rows = [
        [1700000000000 + i * 3600000, 30000 + i, 30100 + i, 29900 + i, 30050 + i, 100 + i]
        for i in range(n)
    ]
    return pd.DataFrame(rows, columns=["timestamp", "open", "high", "low", "close", "volume"])


def test_ten_generation_loop_completes(tmp_path):
    from env.crypto_env import CryptoEnv
    from agent.trainer import Trainer

    env = CryptoEnv(data=make_mock_data(), window_size=60, episode_length=50)
    trainer = Trainer(
        env=env,
        checkpoint_dir=str(tmp_path),
        total_generations=10,
        n_steps=64,
        batch_size=32,
        checkpoint_interval=5,
    )
    trainer.run()

    assert trainer.best_sharpe > -np.inf
    assert any(tmp_path.glob("gen_*.zip"))
