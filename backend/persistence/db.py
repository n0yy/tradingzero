from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker


def build_engine(database_url: str):
    connect_args = {'check_same_thread': False} if database_url.startswith('sqlite') else {}
    return create_engine(database_url, future=True, connect_args=connect_args)


def build_session_factory(engine):
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, class_=Session)
