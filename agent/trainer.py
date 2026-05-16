from pathlib import Path
from queue import Queue
from typing import Optional

import numpy as np
import wandb
from stable_baselines3 import PPO
from stable_baselines3.common.callbacks import BaseCallback

from logger import logger


def _empty_transaction_distribution() -> dict[str, int]:
    return {"buy": 0, "sell": 0, "no_transaction": 0}


def _empty_trade_outcomes() -> dict[str, int]:
    return {"winning": 0, "losing": 0, "flat": 0}


def _promotion_check(
    name: str,
    passed: bool,
    actual: float | int | None,
    target: float | int | None,
    message: str,
) -> dict[str, float | int | str | bool | None]:
    return {
        "name": name,
        "passed": passed,
        "actual": actual,
        "target": target,
        "message": message,
    }


def _transaction_outcome_code(value: str) -> int:
    if value == "BUY":
        return 1
    if value == "SELL":
        return 2
    return 0


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
        min_executed_trades_for_promotion: int = 4,
        min_sell_exits_for_promotion: int = 2,
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
        self.min_executed_trades_for_promotion = min_executed_trades_for_promotion
        self.min_sell_exits_for_promotion = min_sell_exits_for_promotion
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
        self._last_transaction: Optional[dict] = None
        self._generation_transaction_distribution: dict[str, int] = _empty_transaction_distribution()
        self._trade_outcomes: dict[str, int] = _empty_trade_outcomes()

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
        transaction_distribution = _empty_transaction_distribution()
        price_series: list[float] = []
        transaction_outcome_series: list[int] = []
        anchor_results: list[dict] = []
        anchor_specs = list(getattr(self, "evaluation_spec", {}).get("evaluation_anchors", []))

        for ep in range(n_eval_episodes):
            if self._stop:
                break
            obs, _ = self.env.reset()
            done = False
            total_reward = 0.0
            last_balance = self.env.initial_balance
            ep_prices: list[float] = []
            ep_outcomes: list[int] = []
            episode_distribution = _empty_transaction_distribution()
            while not done:
                if self._stop:
                    break
                action, _ = model.predict(obs, deterministic=True)
                obs, reward, terminated, truncated, info = self.env.step(action)
                total_reward += float(reward)
                last_balance = info.get("balance", last_balance)
                done = terminated or truncated
                transaction_outcome = str(info.get("transaction_outcome", "NO_TRANSACTION"))
                if transaction_outcome == "BUY":
                    transaction_distribution["buy"] += 1
                    episode_distribution["buy"] += 1
                elif transaction_outcome == "SELL":
                    transaction_distribution["sell"] += 1
                    episode_distribution["sell"] += 1
                else:
                    transaction_distribution["no_transaction"] += 1
                    episode_distribution["no_transaction"] += 1

                ep_prices.append(float(info.get("price", info.get("next_price", last_balance))))
                ep_outcomes.append(_transaction_outcome_code(transaction_outcome))
                self._stream_step += 1
                self._notify({
                    "kind": "step_batch",
                    "step": self._stream_step,
                    "generation": getattr(self, "_current_generation", 0),
                    "price": float(info.get("price", info.get("next_price", last_balance))),
                    "requested_direction": "HOLD",
                    "requested_size_percent": 0.0,
                    "transaction_outcome": transaction_outcome,
                    "is_transaction": transaction_outcome in ("BUY", "SELL"),
                    "position": float(info.get("position_after", info.get("position", 0.0))),
                    "position_before": float(info.get("position_before", 0.0)),
                    "position_after": float(info.get("position_after", info.get("position", 0.0))),
                    "executed_delta": float(info.get("executed_delta", 0.0)),
                    "balance": float(info.get("balance", last_balance)),
                    "pnl": float(info.get("balance", last_balance)) - float(self.env.initial_balance),
                    "rolling_reward": float(reward),
                    "steps_per_second": 0.0,
                    "equity_curve": [],
                    "cost": float(info.get("cost", 0.0)),
                    "cumulative_buys": self._cumulative_buys,
                    "cumulative_sells": self._cumulative_sells,
                    "transaction_distribution": dict(self._generation_transaction_distribution),
                    "trade_win_rate": self._current_trade_win_rate(),
                    "winning_trades": self._trade_outcomes["winning"],
                    "losing_trades": self._trade_outcomes["losing"],
                    "flat_trades": self._trade_outcomes["flat"],
                    "executed_trade": None,
                    "timestamp": info.get("timestamp"),
                    "phase": "evaluation",
                })

            episode_rewards.append(total_reward)
            episode_final_balances.append(last_balance)
            anchor_spec = anchor_specs[ep] if ep < len(anchor_specs) else {}
            anchor_results.append(
                {
                    "label": anchor_spec.get("label", f"A{ep + 1}"),
                    "start_index": anchor_spec.get("start_index"),
                    "start_timestamp": anchor_spec.get("start_timestamp"),
                    "evaluation_sharpe": float(total_reward),
                    "executed_trade_count": episode_distribution["buy"] + episode_distribution["sell"],
                    "sell_realized_exit_count": episode_distribution["sell"],
                    "final_balance": last_balance,
                    "pnl": last_balance - self.env.initial_balance,
                }
            )

            if ep == 0:
                price_series = ep_prices
                transaction_outcome_series = ep_outcomes

        if not episode_rewards:
            return {
                "sharpe": 0.0,
                "training_sharpe": 0.0,
                "final_balance": self.env.initial_balance,
                "pnl": 0.0,
                "initial_balance": self.env.initial_balance,
                "transaction_distribution": transaction_distribution,
                "executed_trade_count": 0,
                "sell_realized_exit_count": 0,
                "anchor_results": anchor_results,
                "price_series": price_series,
                "transaction_outcome_series": transaction_outcome_series,
            }

        rewards = np.array(episode_rewards, dtype=np.float32)
        std = np.std(rewards)
        sharpe = float(np.mean(rewards) / std) if std != 0 else 0.0
        sharpe = sharpe if np.isfinite(sharpe) else 0.0

        avg_final_balance = float(np.mean(episode_final_balances))
        pnl = avg_final_balance - self.env.initial_balance
        executed_trade_count = transaction_distribution["buy"] + transaction_distribution["sell"]
        sell_realized_exit_count = transaction_distribution["sell"]

        return {
            "sharpe": sharpe,
            "training_sharpe": sharpe,
            "final_balance": avg_final_balance,
            "pnl": pnl,
            "initial_balance": self.env.initial_balance,
            "transaction_distribution": transaction_distribution,
            "executed_trade_count": executed_trade_count,
            "sell_realized_exit_count": sell_realized_exit_count,
            "anchor_results": anchor_results,
            "price_series": price_series,
            "transaction_outcome_series": transaction_outcome_series,
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

    def _current_trade_win_rate(self) -> float:
        realized_exits = sum(self._trade_outcomes.values())
        if realized_exits <= 0:
            return 0.0
        return self._trade_outcomes["winning"] / realized_exits

    def _record_realized_trade(self, executed_trade: dict | None) -> None:
        if executed_trade is None or executed_trade.get("action") != "SELL":
            return

        realized_pnl = float(executed_trade.get("realized_pnl", 0.0))
        if realized_pnl > 0:
            self._trade_outcomes["winning"] += 1
        elif realized_pnl < 0:
            self._trade_outcomes["losing"] += 1
        else:
            self._trade_outcomes["flat"] += 1

    def _build_promotion_gate(
        self,
        evaluation_sharpe: float,
        executed_trade_count: int,
        sell_realized_exit_count: int,
    ) -> tuple[bool, list[dict[str, float | int | str | bool | None]], list[str]]:
        checks: list[dict[str, float | int | str | bool | None]] = []

        if self.best_sharpe == -np.inf:
            checks.append(
                _promotion_check(
                    name="evaluation_sharpe_threshold",
                    passed=False,
                    actual=evaluation_sharpe,
                    target=None,
                    message="No incumbent best yet; baseline was recorded without promotion.",
                )
            )
        else:
            target = self.best_sharpe + self.promote_threshold
            passed = evaluation_sharpe >= target
            checks.append(
                _promotion_check(
                    name="evaluation_sharpe_threshold",
                    passed=passed,
                    actual=evaluation_sharpe,
                    target=target,
                    message=(
                        f"Evaluation Sharpe {evaluation_sharpe:.4f} beat target {target:.4f}."
                        if passed
                        else f"Evaluation Sharpe {evaluation_sharpe:.4f} did not beat target {target:.4f}."
                    ),
                )
            )

        executed_trade_passed = executed_trade_count >= self.min_executed_trades_for_promotion
        checks.append(
            _promotion_check(
                name="executed_trade_count",
                passed=executed_trade_passed,
                actual=executed_trade_count,
                target=self.min_executed_trades_for_promotion,
                message=(
                    f"Executed Trade count {executed_trade_count} met minimum {self.min_executed_trades_for_promotion}."
                    if executed_trade_passed
                    else (
                        f"Executed Trade count {executed_trade_count} was below minimum "
                        f"{self.min_executed_trades_for_promotion}."
                    )
                ),
            )
        )

        sell_exit_passed = sell_realized_exit_count >= self.min_sell_exits_for_promotion
        checks.append(
            _promotion_check(
                name="sell_realized_exit_count",
                passed=sell_exit_passed,
                actual=sell_realized_exit_count,
                target=self.min_sell_exits_for_promotion,
                message=(
                    f"SELL realized exits {sell_realized_exit_count} met minimum {self.min_sell_exits_for_promotion}."
                    if sell_exit_passed
                    else (
                        f"SELL realized exits {sell_realized_exit_count} were below minimum "
                        f"{self.min_sell_exits_for_promotion}."
                    )
                ),
            )
        )

        failed_reasons = [str(check["message"]) for check in checks if not bool(check["passed"])]
        return (len(failed_reasons) == 0), checks, failed_reasons

    def _notify_step(self, generation: int, action, reward: float, info: dict) -> None:
        self._stream_step += 1
        balance = float(info.get("balance", self.env.initial_balance))
        self._equity_curve.append(balance)
        if len(self._equity_curve) > 200:
            self._equity_curve = self._equity_curve[-200:]

        action_array = np.asarray(action)
        direction = int(action_array[0]) if action_array.ndim > 0 else int(action_array)
        requested_size_percent = float(info.get("requested_size_percent", 0.0))
        transaction_outcome = str(info.get("transaction_outcome", "NO_TRANSACTION"))
        is_transaction = bool(info.get("is_transaction", False))
        if transaction_outcome == "BUY":
            self._cumulative_buys += 1
            self._generation_transaction_distribution["buy"] += 1
        elif transaction_outcome == "SELL":
            self._cumulative_sells += 1
            self._generation_transaction_distribution["sell"] += 1
        else:
            self._generation_transaction_distribution["no_transaction"] += 1

        executed_trade = info.get("executed_trade")
        if executed_trade is not None:
            self._last_transaction = dict(executed_trade)
            self._record_realized_trade(executed_trade)
        price = float(info.get("price", info.get("next_price", balance)))
        self._notify({
            "kind": "step_batch",
            "step": self._stream_step,
            "generation": generation,
            "price": price,
            "requested_direction": info.get("requested_direction", "HOLD" if direction == 0 else "BUY" if direction == 1 else "SELL"),
            "requested_size_percent": requested_size_percent,
            "transaction_outcome": transaction_outcome,
            "is_transaction": is_transaction,
            "position": float(info.get("position_after", info.get("position", 0.0))),
            "position_before": float(info.get("position_before", 0.0)),
            "position_after": float(info.get("position_after", info.get("position", 0.0))),
            "executed_delta": float(info.get("executed_delta", 0.0)),
            "balance": balance,
            "pnl": balance - float(self.env.initial_balance),
            "rolling_reward": float(reward),
            "steps_per_second": 0.0,
            "equity_curve": list(self._equity_curve),
            "cost": float(info.get("cost", 0.0)),
            "cumulative_buys": self._cumulative_buys,
            "cumulative_sells": self._cumulative_sells,
            "transaction_distribution": dict(self._generation_transaction_distribution),
            "trade_win_rate": self._current_trade_win_rate(),
            "winning_trades": self._trade_outcomes["winning"],
            "losing_trades": self._trade_outcomes["losing"],
            "flat_trades": self._trade_outcomes["flat"],
            "executed_trade": dict(executed_trade) if executed_trade is not None else None,
            "timestamp": info.get("timestamp"),
            "phase": "training",
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

            self._generation_transaction_distribution = _empty_transaction_distribution()

            logger.info(f"Generation {generation + 1}/{self.total_generations}")
            self._current_generation = generation + 1
            self._model.learn(
                total_timesteps=self.n_steps,
                reset_num_timesteps=False,
                callback=TrainingStreamCallback(self, generation + 1),
            )

            eval_result = self._evaluate(self._model)
            training_sharpe = float(eval_result.get("training_sharpe", eval_result["sharpe"]))
            evaluation_sharpe = float(eval_result["sharpe"])
            final_balance = eval_result["final_balance"]
            pnl = eval_result["pnl"]
            initial_balance = eval_result["initial_balance"]
            transaction_distribution = eval_result.get("transaction_distribution", _empty_transaction_distribution())
            executed_trade_count = int(eval_result.get("executed_trade_count", 0))
            sell_realized_exit_count = int(eval_result.get("sell_realized_exit_count", 0))
            anchor_results = eval_result.get("anchor_results", [])
            price_series = eval_result.get("price_series", [])
            transaction_outcome_series = eval_result.get("transaction_outcome_series", [])
            trade_win_rate = self._current_trade_win_rate()
            logger.info(
                f"  Train Sharpe: {training_sharpe:.4f} | Eval Sharpe: {evaluation_sharpe:.4f} "
                f"(best eval: {self.best_sharpe:.4f}) | "
                f"Balance: {final_balance:.2f} | PnL: {pnl:+.2f} | trade_win={trade_win_rate*100:.0f}%"
            )

            if (generation + 1) % self.checkpoint_interval == 0:
                ckpt = self._save_checkpoint(self._model, f"gen_{generation + 1:04d}")
                self._prune_old_checkpoints()
                logger.info(f"  Checkpoint saved: {ckpt}")

            promoted, promotion_gate_checks, promotion_gate_reasons = self._build_promotion_gate(
                evaluation_sharpe=evaluation_sharpe,
                executed_trade_count=executed_trade_count,
                sell_realized_exit_count=sell_realized_exit_count,
            )
            for check in promotion_gate_checks:
                status = "PASS" if check["passed"] else "FAIL"
                logger.info(f"  Gate [{status}] {check['name']}: {check['message']}")
            if promoted:
                self.best_sharpe = evaluation_sharpe
                self.best_checkpoint = self._save_checkpoint(self._model, "best")
                logger.info(f"  Promotion decision: PROMOTED | new best eval sharpe {self.best_sharpe:.4f}")
            else:
                logger.info("  Promotion decision: NOT PROMOTED | " + " | ".join(promotion_gate_reasons))

            if self.best_sharpe == -np.inf:
                self.best_sharpe = evaluation_sharpe

            if self.wandb_project:
                wandb.log({
                    "generation": generation + 1,
                    "training_sharpe": training_sharpe,
                    "evaluation_sharpe": evaluation_sharpe,
                    "best_evaluation_sharpe": self.best_sharpe,
                    "promoted": int(promoted),
                    "evaluation_executed_trade_count": executed_trade_count,
                    "evaluation_sell_realized_exit_count": sell_realized_exit_count,
                    "final_balance": final_balance,
                    "pnl": pnl,
                })

            self._notify({
                "generation": generation + 1,
                "training_sharpe": training_sharpe,
                "evaluation_sharpe": evaluation_sharpe,
                "best_evaluation_sharpe": self.best_sharpe,
                "promoted": promoted,
                "total_generations": self.total_generations,
                "final_balance": final_balance,
                "pnl": pnl,
                "initial_balance": initial_balance,
                "evaluation_executed_trade_count": executed_trade_count,
                "evaluation_sell_realized_exit_count": sell_realized_exit_count,
                "promotion_gate_checks": promotion_gate_checks,
                "promotion_gate_reasons": promotion_gate_reasons,
                "anchor_results": anchor_results,
                "transaction_distribution": dict(self._generation_transaction_distribution),
                "price_series": price_series,
                "action_series": transaction_outcome_series,
                "action_counts": transaction_distribution,
                "cumulative_buys": self._cumulative_buys,
                "cumulative_sells": self._cumulative_sells,
                "trade_win_rate": trade_win_rate,
                "winning_trades": self._trade_outcomes["winning"],
                "losing_trades": self._trade_outcomes["losing"],
                "flat_trades": self._trade_outcomes["flat"],
                "last_transaction": dict(self._last_transaction) if self._last_transaction is not None else None,
            })

        if self.wandb_project:
            wandb.finish()

        logger.info("Training complete.")
