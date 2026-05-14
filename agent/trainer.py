from pathlib import Path
from queue import Queue
from typing import Optional

import numpy as np
import wandb
from stable_baselines3 import PPO

from logger import logger


class Trainer:
    def __init__(
        self,
        env,
        checkpoint_dir: str = "agent/checkpoints",
        total_generations: int = 500,
        learning_rate: float = 3e-4,
        n_steps: int = 2048,
        batch_size: int = 64,
        clip_range: float = 0.2,
        promote_threshold: float = 0.05,
        checkpoint_interval: int = 10,
        update_queue: Optional[Queue] = None,
        wandb_project: Optional[str] = None,
    ):
        self.env = env
        self.checkpoint_dir = Path(checkpoint_dir)
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
        self.total_generations = total_generations
        self.learning_rate = learning_rate
        self.n_steps = n_steps
        self.batch_size = batch_size
        self.clip_range = clip_range
        self.promote_threshold = promote_threshold
        self.checkpoint_interval = checkpoint_interval
        self.update_queue = update_queue
        self.wandb_project = wandb_project

        self.best_sharpe: float = -np.inf
        self.best_checkpoint: Optional[Path] = None
        self._stop = False
        self._model: Optional[PPO] = None

    def _build_model(self) -> PPO:
        return PPO(
            "MlpPolicy",
            self.env,
            learning_rate=self.learning_rate,
            n_steps=self.n_steps,
            batch_size=self.batch_size,
            clip_range=self.clip_range,
            ent_coef=0.01,
            verbose=0,
        )

    def _evaluate(self, model: PPO, n_eval_episodes: int = 5) -> dict:
        episode_rewards: list[float] = []
        episode_final_balances: list[float] = []

        for _ in range(n_eval_episodes):
            obs, _ = self.env.reset()
            done = False
            total_reward = 0.0
            last_balance = self.env.initial_balance
            while not done:
                action, _ = model.predict(obs, deterministic=False)
                obs, reward, terminated, truncated, info = self.env.step(int(action))
                total_reward += float(reward)
                last_balance = info.get("balance", last_balance)
                done = terminated or truncated
            episode_rewards.append(total_reward)
            episode_final_balances.append(last_balance)

        rewards = np.array(episode_rewards, dtype=np.float32)
        std = np.std(rewards)
        sharpe = float(np.mean(rewards) / std) if std != 0 else 0.0
        sharpe = sharpe if np.isfinite(sharpe) else 0.0

        avg_final_balance = float(np.mean(episode_final_balances))
        pnl = avg_final_balance - self.env.initial_balance

        return {
            "sharpe": sharpe,
            "final_balance": avg_final_balance,
            "pnl": pnl,
            "initial_balance": self.env.initial_balance,
        }

    def _save_checkpoint(self, model: PPO, name: str) -> Path:
        path = self.checkpoint_dir / name
        model.save(str(path))
        self._validate_checkpoint(path)
        return path

    def _validate_checkpoint(self, path: Path) -> None:
        loaded = PPO.load(str(path), env=self.env)
        obs, _ = self.env.reset()
        loaded.predict(obs, deterministic=True)

    def _prune_old_checkpoints(self, keep: int = 3) -> None:
        checkpoints = sorted(self.checkpoint_dir.glob("gen_*.zip"))
        for old in checkpoints[:-keep]:
            old.unlink()

    def _notify(self, payload: dict) -> None:
        if self.update_queue is not None:
            self.update_queue.put(payload)

    def stop(self) -> None:
        self._stop = True

    def run(self) -> None:
        if self.wandb_project:
            wandb.init(
                project=self.wandb_project,
                config={
                    "learning_rate": self.learning_rate,
                    "n_steps": self.n_steps,
                    "batch_size": self.batch_size,
                    "clip_range": self.clip_range,
                    "promote_threshold": self.promote_threshold,
                    "total_generations": self.total_generations,
                },
            )

        self._model = self._build_model()

        for generation in range(self.total_generations):
            if self._stop:
                break

            logger.info(f"Generation {generation + 1}/{self.total_generations}")
            self._model.learn(total_timesteps=self.n_steps, reset_num_timesteps=False)

            eval_result = self._evaluate(self._model)
            current_sharpe = eval_result["sharpe"]
            final_balance = eval_result["final_balance"]
            pnl = eval_result["pnl"]
            initial_balance = eval_result["initial_balance"]
            logger.info(f"  Sharpe: {current_sharpe:.4f} (best: {self.best_sharpe:.4f}) | Balance: {final_balance:.2f} | PnL: {pnl:+.2f}")

            if (generation + 1) % self.checkpoint_interval == 0:
                ckpt = self._save_checkpoint(self._model, f"gen_{generation + 1:04d}")
                self._prune_old_checkpoints()
                logger.info(f"  Checkpoint saved: {ckpt}")

            promoted = (
                self.best_sharpe != -np.inf
                and current_sharpe - self.best_sharpe >= self.promote_threshold
            )
            if promoted:
                self.best_sharpe = current_sharpe
                self.best_checkpoint = self._save_checkpoint(self._model, "best")
                logger.info(f"  Promoted! New best Sharpe: {self.best_sharpe:.4f}")

            if self.best_sharpe == -np.inf:
                self.best_sharpe = current_sharpe

            if self.wandb_project:
                wandb.log({
                    "generation": generation + 1,
                    "current_sharpe": current_sharpe,
                    "best_sharpe": self.best_sharpe,
                    "promoted": int(promoted),
                    "final_balance": final_balance,
                    "pnl": pnl,
                })

            self._notify({
                "generation": generation + 1,
                "current_sharpe": current_sharpe,
                "best_sharpe": self.best_sharpe,
                "promoted": promoted,
                "total_generations": self.total_generations,
                "final_balance": final_balance,
                "pnl": pnl,
                "initial_balance": initial_balance,
            })

        if self.wandb_project:
            wandb.finish()

        logger.info("Training complete.")
