"""시드 데이터: 좌석 40석(A~D열 × 10), 관리자 1명, 기본 운영 정책, 데모 학생 2명.

    python -m scripts.seed
여러 번 실행해도 중복 생성되지 않는다.
"""

from sqlalchemy import select

from app.core.config import get_settings
from app.core.database import SessionLocal
from app.core.security import hash_password
from app.models import AccountStatus, OperationPolicy, Role, Seat, User

ROWS, COLS = "ABCD", 10
DEMO_STUDENTS = [("202200001", "student1@example.ac.kr"), ("202200002", "student2@example.ac.kr")]
DEMO_PASSWORD = "Student!234"


def run():
    s = get_settings()
    with SessionLocal() as db, db.begin():
        if db.get(OperationPolicy, 1) is None:
            db.add(OperationPolicy(id=1))

        existing = set(db.scalars(select(Seat.seat_number)))
        for r, row in enumerate(ROWS, start=1):
            for c in range(1, COLS + 1):
                num = f"{row}-{c:02d}"
                if num not in existing:
                    db.add(Seat(seat_number=num, grid_row=r, grid_col=c, enabled=True))

        def ensure_user(login_id, **kw):
            if db.scalar(select(User).where(User.login_id == login_id)) is None:
                db.add(User(login_id=login_id, account_status=AccountStatus.ACTIVE, **kw))

        ensure_user(
            s.seed_admin_login_id,
            password_hash=hash_password(s.seed_admin_password),
            role=Role.ROLE_ADMIN,
            name="관리자",
        )
        for no, email in DEMO_STUDENTS:
            ensure_user(
                no,
                student_no=no,
                email=email,
                password_hash=hash_password(DEMO_PASSWORD),
                role=Role.ROLE_STUDENT,
                name=f"데모{no[-1]}",
            )
    print(
        f"seed done: seats={len(ROWS) * COLS}, admin={s.seed_admin_login_id}, "
        f"students={[n for n, _ in DEMO_STUDENTS]} (pw: {DEMO_PASSWORD})"
    )


if __name__ == "__main__":
    run()
