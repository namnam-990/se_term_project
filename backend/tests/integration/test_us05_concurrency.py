"""US-05 AC2 — 동일 좌석·시간 동시 예약 시 1건만 성공 (MySQL 필요, 명세서 4.4 트랜잭션 잠금).

실행 (⚠️ 테이블을 지우고 다시 만드므로 반드시 테스트 전용 DB lsrs_test 사용):
    export TEST_DATABASE_URL=mysql+pymysql://lsrs:lsrs_pw@127.0.0.1:3306/lsrs_test
    pytest -m integration -v
데모에서 '자동 테스트 실행 화면'으로 보여줄 1순위 테스트입니다.
"""

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

import app.models  # noqa: F401
from app.core.clock import FixedClock
from app.core.database import Base
from app.core.exceptions import ConflictError
from app.core.security import hash_password
from app.models import AccountStatus, OperationPolicy, Reservation, Role, Seat, User
from app.schemas.reservation import ReservationCreateRequest
from app.services.reservation_service import ReservationService

pytestmark = pytest.mark.integration

N = 10  # 동시에 요청하는 학생 수


def test_us05_ac2_concurrent_same_seat_only_one_succeeds(mysql_url):
    engine = create_engine(mysql_url, isolation_level="READ COMMITTED", pool_size=N + 2)
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    make_session = sessionmaker(bind=engine, expire_on_commit=False)

    with make_session() as db:
        db.add(OperationPolicy(id=1))
        seat = Seat(seat_number="A-01", grid_row=1, grid_col=1, enabled=True)
        db.add(seat)
        users = [
            User(
                login_id=f"2022{i:05d}",
                student_no=f"2022{i:05d}",
                email=f"s{i}@example.ac.kr",
                password_hash=hash_password("Student!234"),
                role=Role.ROLE_STUDENT,
                account_status=AccountStatus.ACTIVE,
            )
            for i in range(N)
        ]
        db.add_all(users)
        db.commit()
        seat_id, user_ids = seat.id, [u.id for u in users]

    clock = FixedClock(datetime(2026, 11, 20, 9, 0))
    req = ReservationCreateRequest(
        seat_id=seat_id,
        start_at=datetime(2026, 11, 20, 10, 0),
        end_at=datetime(2026, 11, 20, 12, 0),
    )

    def attempt(user_id: int) -> str:
        with make_session() as db:
            user = db.get(User, user_id)
            try:
                ReservationService(db, clock).create(user, req)
                return "ok"
            except ConflictError:
                return "conflict"

    with ThreadPoolExecutor(max_workers=N) as pool:
        results = list(pool.map(attempt, user_ids))

    assert results.count("ok") == 1
    assert results.count("conflict") == N - 1
    with make_session() as db:
        assert len(db.scalars(select(Reservation)).all()) == 1  # 중복 배정 0건
