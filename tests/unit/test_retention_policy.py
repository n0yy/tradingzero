from datetime import UTC, datetime, timedelta

from backend.persistence.db import build_engine, build_session_factory
from backend.persistence.models import Base, Run
from backend.persistence.repository import Repository


def test_prune_removes_data_older_than_90_days(tmp_path):
    db_url = f"sqlite:///{tmp_path / 'retention.db'}"
    engine = build_engine(db_url)
    Base.metadata.create_all(bind=engine)
    session_factory = build_session_factory(engine)

    with session_factory() as session:
        repo = Repository(session)
        repo.create_run('old-run', 'done', None)
        repo.add_event('old-run', 'done', 'old done')
        repo.add_error('old-run', 'old_error', 'old message')

        old = session.get(Run, 'old-run')
        old.started_at = datetime.now(UTC) - timedelta(days=120)
        old.finished_at = datetime.now(UTC) - timedelta(days=119)
        session.commit()

    with session_factory() as session:
        pruned = Repository(session).prune_older_than_days(90)
        session.commit()
        assert pruned == 1

    with session_factory() as session:
        assert session.get(Run, 'old-run') is None
