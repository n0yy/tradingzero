from backend.runners import InMemoryRunnerAdapter, TrainerRunnerAdapter


class _DummyTrainer:
    def __init__(self):
        self.stopped = False
        self.ran = False

    def run(self):
        self.ran = True

    def stop(self):
        self.stopped = True


def test_trainer_runner_adapter_runs_built_trainer(mocker):
    trainer = _DummyTrainer()
    mocker.patch('backend.runners.build_trainer_runtime', return_value=trainer)

    adapter = TrainerRunnerAdapter(config_path='config.yaml', resume=True)
    adapter.run()

    assert trainer.ran is True


def test_trainer_runner_adapter_stop_propagates_to_trainer(mocker):
    trainer = _DummyTrainer()
    mocker.patch('backend.runners.build_trainer_runtime', return_value=trainer)

    adapter = TrainerRunnerAdapter(config_path='config.yaml', resume=True)
    adapter.run()
    adapter.stop()

    assert trainer.stopped is True


def test_inmemory_runner_emits_training_updates_until_stopped():
    received: list[dict] = []

    def on_update(payload: dict) -> None:
        received.append(payload)

    adapter = InMemoryRunnerAdapter(
        on_update=on_update,
        tick_interval=0.01,
        step_interval=0.005,
        total_generations=5,
    )

    import threading
    thread = threading.Thread(target=adapter.run, daemon=True)
    thread.start()

    import time
    time.sleep(0.1)
    adapter.stop()
    thread.join(timeout=1.0)

    generation_updates = [p for p in received if p.get('kind') == 'generation_update']
    assert len(generation_updates) >= 2
    sample = generation_updates[0]
    assert 'generation' in sample
    assert 'current_sharpe' in sample
    assert 'final_balance' in sample
    assert 'action_counts' in sample
    assert {'buy', 'hold', 'sell'} <= set(sample['action_counts'].keys())


def test_inmemory_runner_emits_step_batch_faster_than_generations():
    received: list[dict] = []
    adapter = InMemoryRunnerAdapter(
        on_update=received.append,
        tick_interval=0.05,
        step_interval=0.005,
        total_generations=4,
    )

    import threading
    thread = threading.Thread(target=adapter.run, daemon=True)
    thread.start()

    import time
    time.sleep(0.15)
    adapter.stop()
    thread.join(timeout=1.0)

    step_batches = [p for p in received if p.get('kind') == 'step_batch']
    generation_updates = [p for p in received if p.get('kind') == 'generation_update']

    assert len(step_batches) > len(generation_updates)
    assert len(step_batches) >= 5
    sample = step_batches[0]
    for key in ('step', 'price', 'last_action', 'position', 'balance', 'pnl', 'rolling_reward', 'steps_per_second', 'equity_curve'):
        assert key in sample


