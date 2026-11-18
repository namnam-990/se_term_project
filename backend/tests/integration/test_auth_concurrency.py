"""US-01·03 MySQL 동시성. 자체 생성 계정만 정리하며 기존 테이블을 초기화하지 않는다."""

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from threading import Barrier
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, delete, select
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker

from app.core.clock import FixedClock
from app.core.database import Base
from app.core.exceptions import AppError
from app.core.security import hash_password
from app.models import AccountStatus, AuthSession, EmailVerification, User
from app.schemas.auth import LoginRequest, SignupRequest
from app.services.auth_service import AuthService
from app.services.mail import FakeMailSender

pytestmark = pytest.mark.integration


@pytest.fixture
def auth_mysql(mysql_url):
    if not (make_url(mysql_url).database or "").endswith("_test"):
        pytest.fail("이름이 _test로 끝나는 전용 DB에서만 실행하세요.")
    engine = create_engine(mysql_url, isolation_level="READ COMMITTED", pool_size=8)
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    login_id = "auth_" + uuid4().hex[:12]
    try:
        yield factory, login_id
    finally:
        with factory() as db:
            ids = select(User.id).where(User.login_id == login_id)
            db.execute(delete(AuthSession).where(AuthSession.user_id.in_(ids)))
            db.execute(delete(EmailVerification).where(EmailVerification.user_id.in_(ids)))
            db.execute(delete(User).where(User.login_id == login_id))
            db.commit()
        engine.dispose()


def test_us03_concurrent_failures_are_committed_once_each(auth_mysql):
    factory, login_id = auth_mysql
    with factory() as db:
        db.add(
            User(
                login_id=login_id,
                student_no=login_id,
                email=f"{login_id}@example.ac.kr",
                password_hash=hash_password("Student!234"),
                account_status=AccountStatus.ACTIVE,
            )
        )
        db.commit()
    barrier = Barrier(6)

    def attempt(_):
        with factory() as db:
            svc = AuthService(db, FixedClock(datetime(2026, 11, 20, 9)), FakeMailSender())
            barrier.wait(timeout=10)
            try:
                svc.login(LoginRequest(login_id=login_id, password="Wrong!234"))
            except AppError as exc:
                return exc.code

    with ThreadPoolExecutor(max_workers=6) as pool:
        results = list(pool.map(attempt, range(6)))
    assert results.count("LOGIN_FAILED") == 5
    assert results.count("ACCOUNT_LOCKED") == 1
    with factory() as db:
        user = db.scalar(select(User).where(User.login_id == login_id))
        assert user.failed_login_count == 6 and user.account_status == AccountStatus.LOCKED


def test_us01_concurrent_duplicate_signup_returns_conflict(auth_mysql):
    factory, login_id = auth_mysql
    req = SignupRequest(
        student_no=login_id, email=f"{login_id}@example.ac.kr", password="Student!234"
    )
    barrier = Barrier(2)

    def attempt(_):
        with factory() as db:
            svc = AuthService(db, FixedClock(datetime(2026, 11, 20, 9)), FakeMailSender())
            barrier.wait(timeout=10)
            try:
                svc.signup(req)
                return "created"
            except AppError as exc:
                return exc.code

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(attempt, range(2)))
    assert results.count("created") == 1
    assert results.count("DUPLICATE_STUDENT_NO") == 1
