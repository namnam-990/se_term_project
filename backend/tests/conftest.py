"""공통 픽스처.

- unit: DB 없이 SQLite 메모리 DB 사용 (빠름, 로직 검증용)
- integration: TEST_DATABASE_URL(MySQL) 필요. 없으면 자동 skip.
  FOR UPDATE 잠금·동시성은 SQLite로 검증 불가 → 반드시 MySQL 통합 테스트로.
"""

import os
from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401
from app.core.clock import FixedClock, get_clock
from app.core.database import Base, get_db
from app.core.security import create_access_token, hash_password, new_token, sha256
from app.main import app
from app.models import (
    AccountStatus,
    AuthSession,
    OperationPolicy,
    Reservation,
    ReservationStatus,
    Role,
    Seat,
    User,
)
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


# ───────────────────────── 데이터 준비 헬퍼 (US별 테스트 공용) ─────────────────────────

DEFAULT_PASSWORD = "Student!234"


@pytest.fixture
def policy(db_session) -> OperationPolicy:
    """명세서 기본값 정책 (평상시 +7일·4시간 / 시험 +1일·3시간, 09~22시·60분)."""
    p = OperationPolicy(id=1)
    db_session.add(p)
    db_session.commit()
    return p


@pytest.fixture
def seats(db_session) -> list[Seat]:
    """A-01 ~ A-04 좌석 4개."""
    items = [Seat(seat_number=f"A-0{i}", grid_row=1, grid_col=i, enabled=True) for i in range(1, 5)]
    db_session.add_all(items)
    db_session.commit()
    return items


@pytest.fixture
def make_user(db_session):
    """make_user("202200001") → ACTIVE 학생. status·role·password로 변경 가능."""

    def _make(
        login_id: str = "202200001",
        *,
        status: AccountStatus = AccountStatus.ACTIVE,
        role: Role = Role.ROLE_STUDENT,
        password: str = DEFAULT_PASSWORD,
        email: str | None = None,
    ):
        is_student = role == Role.ROLE_STUDENT
        user = User(
            login_id=login_id,
            student_no=login_id if is_student else None,
            email=email or (f"{login_id}@example.ac.kr" if is_student else None),
            password_hash=hash_password(password),
            role=role,
            account_status=status,
        )
        db_session.add(user)
        db_session.commit()
        return user

    return _make


@pytest.fixture
def auth_headers(db_session, clock):
    """auth_headers(user) → {"Authorization": "Bearer ..."}

    US-02(로그인) 구현 전에도 다른 US를 테스트할 수 있도록 세션과 토큰을 직접 만든다.
    Bearer 호출이라 CSRF 검사는 생략된다.
    """

    def _headers(user):
        session = AuthSession(
            user_id=user.id,
            refresh_token_hash=sha256(new_token()),
            expires_at=clock.now() + timedelta(days=7),
        )
        db_session.add(session)
        db_session.commit()
        token = create_access_token(user.id, user.role.value, session.id)
        return {"Authorization": f"Bearer {token}"}

    return _headers


@pytest.fixture
def make_reservation(db_session):
    """make_reservation(user, seat, "10:00", "12:00", status=RESERVED) — 고정 날짜 2026-11-20."""

    def _make(user, seat, start: str, end: str, status=ReservationStatus.RESERVED, day: int = 20):
        def at(hm: str) -> datetime:
            h, m = map(int, hm.split(":"))
            return datetime(2026, 11, day, h, m)

        r = Reservation(
            user_id=user.id, seat_id=seat.id, start_at=at(start), end_at=at(end), status=status
        )
        db_session.add(r)
        db_session.commit()
        return r

    return _make
