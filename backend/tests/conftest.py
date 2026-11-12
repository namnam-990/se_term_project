"""공통 픽스처.

- unit: DB 없이 SQLite 메모리 DB 사용 (빠름, 로직 검증용)
- integration: TEST_DATABASE_URL(MySQL) 필요. 없으면 자동 skip.
  FOR UPDATE 잠금·동시성은 SQLite로 검증 불가 → 반드시 MySQL 통합 테스트로.
"""

import os
from datetime import datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401
from app.core.clock import FixedClock, get_clock
from app.core.database import Base, get_db
from app.main import app
from app.services.mail import FakeMailSender, get_mail_sender


@pytest.fixture
def clock() -> FixedClock:
    return FixedClock(datetime(2026, 11, 20, 9, 0, 0))


@pytest.fixture
def mail() -> FakeMailSender:
    return FakeMailSender()


@pytest.fixture
def db_session():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


@pytest.fixture
def client(db_session, clock, mail):
    app.dependency_overrides[get_db] = lambda: db_session
    app.dependency_overrides[get_clock] = lambda: clock
    app.dependency_overrides[get_mail_sender] = lambda: mail
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def mysql_url():
    url = os.getenv("TEST_DATABASE_URL")
    if not url:
        pytest.skip("TEST_DATABASE_URL 미설정 → MySQL 통합 테스트 생략")
    return url
