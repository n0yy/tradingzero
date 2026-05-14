from pathlib import Path
from queue import Queue
from typing import Optional

import numpy as np
import wandb
from stable_baselines3 import PPO
from stable_baselines3.common.callbacks import BaseCallback

from logger import logger


class TrainingStreamCallback(BaseCallback):
    def __init__(self, trainer: "Trainer", generation: int):
        super().__init__()
        self.trainer = trainer
        self.generation = generation

    def _on_step(self) -> bool:
        infos = self.locals.get("infos") or []
        actions = self.locals.get("actions")
        rewards = self.locals.get("rewards")
        if not infos:
            return not self.trainer._stop

        info = infos[0] or {}
        action = actions[0] if actions is not None and len(actions) > 0 else 0
        reward = rewards[0] if rewards is not None and len(rewards) > 0 else 0.0
        self.trainer._notify_step(self.generation, action, reward, info)
        return not self.trainer._stop


class Trainer:
    def __init__(
        self,
        env,
        checkpoint_dir: str = "agent/checkpoints",
        total_generations: int = 500,
        learning_rate: float = 3e-4,
        n_steps: int = 2048,
        batch_size: int = 64,
        clip_range: float = 0.1,
        promote_threshold: float = 0.05,
        checkpoint_interval: int = 10,
        update_queue: Optional[Queue] = None,
        wandb_project: Optional[str] = None,
        resume: bool = True,
        resume_from: Optional[str] = None,
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

        self.resume = resume
        self.resume_from = Path(resume_from) if resume_from else None
        self.best_sharpe: float = -np.inf
        self.best_checkpoint: Optional[Path] = None
        self._stop = False
        self._model: Optional[PPO] = None
        self._cumulative_buys: int = 0
        self._cumulative_sells: int = 0
        self._stream_step: int = 0
        self._equity_curve: list[float] = [float(env.initial_balance)]

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
        wins = 0
        action_counts = {"buy": 0, "hold": 0, "sell": 0}
        price_series: list[float] = []
        action_series: list[int] = []

        for ep in range(n_eval_episodes):
            if self._stop:
                break
            obs, _ = self.env.reset()
            done = False
            total_reward = 0.0
            last_balance = self.env.initial_balance
            ep_prices: list[float] = []
            ep_actions: list[int] = []
            while not done:
                if self._stop:
                    break
                action, _ = model.predict(obs, deterministic=False)
                action_int = int(action) if np.ndim(action) == 0 else int(action[0])
                obs, reward, terminated, truncated, info = self.env.step(action)
                total_reward += float(reward)
                last_balance = info.get("balance", last_balance)
                done = terminated or truncated

                if action_int == 0:
                    action_counts["hold"] += 1
                elif action_int == 1:
                    action_counts["buy"] += 1
                else:
                    action_counts["sell"] += 1

                ep_prices.append(float(info.get("balance", last_balance)))
                ep_actions.append(action_int)

            episode_rewards.append(total_reward)
            episode_final_balances.append(last_balance)
            if last_balance > self.env.initial_balance:
                wins += 1

            if ep == 0:
                price_series = ep_prices
                action_series = ep_actions

        if not episode_rewards:
            return {
                "sharpe": 0.0,
                "final_balance": self.env.initial_balance,
                "pnl": 0.0,
                "initial_balance": self.env.initial_balance,
                "win_rate": 0.0,
                "action_counts": action_counts,
                "price_series": price_series,
                "action_series": action_series,
            }

        rewards = np.array(episode_rewards, dtype=np.float32)
        std = np.std(rewards)
        sharpe = float(np.mean(rewards) / std) if std != 0 else 0.0
        sharpe = sharpe if np.isfinite(sharpe) else 0.0

        avg_final_balance = float(np.mean(episode_final_balances))
        pnl = avg_final_balance - self.env.initial_balance
        win_rate = wins / n_eval_episodes if n_eval_episodes > 0 else 0.0

        return {
            "sharpe": sharpe,
            "final_balance": avg_final_balance,
            "pnl": pnl,
            "initial_balance": self.env.initial_balance,
            "win_rate": win_rate,
            "action_counts": action_counts,
            "price_series": price_series,
            "action_series": action_series,
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

    def _notify_step(self, generation: int, action, reward: float, info: dict) -> None:
        self._stream_step += 1
        balance = float(info.get("balance", self.env.initial_balance))
        self._equity_curve.append(balance)
        if len(self._equity_curve) > 200:
            self._equity_curve = self._equity_curve[-200:]

        action_array = np.asarray(action)
        direction = int(action_array[0]) if action_array.ndim > 0 else int(action_array)
        price = float(info.get("price", info.get("next_price", balance)))
        self._notify({
            "kind": "step_batch",
            "step": self._stream_step,
            "generation": generation,
            "price": price,
            "last_action": direction,
            "position": float(info.get("position", 0.0)),
            "balance": balance,
            "pnl": balance - float(self.env.initial_balance),
            "rolling_reward": float(reward),
            "steps_per_second": 0.0,
            "equity_curve": list(self._equity_curve),
        })

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

        best_path = self.checkpoint_dir / "best.zip"
        if self.resume_from is not None:
            if not self.resume_from.exists():
                raise FileNotFoundError(f"checkpoint not found: {self.resume_from}")
            logger.info(f"Resuming from explicit checkpoint: {self.resume_from}")
            self._model = PPO.load(str(self.resume_from), env=self.env)
        elif self.resume and best_path.exists():
            logger.info(f"Resuming from checkpoint: {best_path}")
            self._model = PPO.load(str(best_path), env=self.env)
        else:
            if not self.resume:
                logger.info("Starting from scratch (--no-resume)")
            else:
                logger.info("No checkpoint found — starting from scratch")
            self._model = self._build_model()

        for generation in range(self.total_generations):
            if self._stop:
                break

            logger.info(f"Generation {generation + 1}/{self.total_generations}")
            self._model.learn(
                total_timesteps=self.n_steps,
                reset_num_timesteps=False,
                callback=TrainingStreamCallback(self, generation + 1),
            )

            eval_result = self._evaluate(self._model)
            current_sharpe = eval_result["sharpe"]
            final_balance = eval_result["final_balance"]
            pnl = eval_result["pnl"]
            initial_balance = eval_result["initial_balance"]
            win_rate = eval_result.get("win_rate", 0.0)
            action_counts = eval_result.get("action_counts", {"buy": 0, "hold": 0, "sell": 0})
            price_series = eval_result.get("price_series", [])
            action_series = eval_result.get("action_series", [])
            self._cumulative_buys += action_counts.get("buy", 0)
            self._cumulative_sells += action_counts.get("sell", 0)
            logger.info(f"  Sharpe: {current_sharpe:.4f} (best: {self.best_sharpe:.4f}) | Balance: {final_balance:.2f} | PnL: {pnl:+.2f} | win={win_rate*100:.0f}%")

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
                "win_rate": win_rate,
                "action_counts": action_counts,
                "price_series": price_series,
                "action_series": action_series,
                "cumulative_buys": self._cumulative_buys,
                "cumulative_sells": self._cumulative_sells,
            })

        if self.wandb_project:
            wandb.finish()

        logger.info("Training complete.")
