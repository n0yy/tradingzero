from __future__ import annotations

from fastapi.testclient import TestClient

from backend.app import create_app
from backend.evaluation_spec import RunEvaluationPlan
from tests.unit.test_evaluation_spec import make_config, make_market_data


def test_run_start_persists_evaluation_spec_and_exposes_it_in_status_and_history(tmp_path):
    data = make_market_data()

    def evaluation_plan_factory(_config: dict) -> RunEvaluationPlan:
        from backend.evaluation_spec import build_run_evaluation_plan

        return build_run_evaluation_plan(
            config=make_config(),
            data=data,
            training_seed=101,
            evaluation_seed=202,
        )

    db_url = f"sqlite:///{tmp_path / 'app.db'}"
    app = create_app(
        database_url=db_url,
        config_path=str(tmp_path / 'missing.yaml'),
        runner_mode='inmemory',
        evaluation_plan_factory_override=evaluation_plan_factory,
    )
    client = TestClient(app)

    start = client.post('/runs/start')
    assert start.status_code == 202
    start_spec = start.json()['evaluation_spec']
    assert start_spec['training_seed'] == 101
    assert start_spec['evaluation_seed'] == 202

    status = client.get('/runs/status')
    assert status.status_code == 200
    assert status.json()['evaluation_spec'] == start_spec

    history = client.get('/runs')
    assert history.status_code == 200
    assert history.json()['runs'][0]['evaluation_spec'] == start_spec
    assert history.json()['runs'][0]['evaluation_spec']['training_slice']['end_index'] < history.json()['runs'][0][
        'evaluation_spec'
    ]['evaluation_slice']['start_index']
