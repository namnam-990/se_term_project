"""시드 데이터 — 데모 준비물 (데모 루브릭 '즉시 실행 가능한 환경 준비').

    python -m scripts.seed
    python -m scripts.seed --reset-policy   # 운영 정책을 현재 기본값(06~23시·30분 등)으로 되돌림

여러 번 실행해도 중복 생성되지 않는다. 생성 내용:
- 운영 정책 1행 (평상시 +7일·4시간 / 시험 +1일·3시간 / 운영 06:00~23:00 / 30분 단위, D-11)
  이미 정책이 있으면 그대로 둔다. 기본값이 바뀌었을 때는 --reset-policy 로 갱신
- 좌석 40석 (A~D열 × 10)
- 계정 (비밀번호는 아래 표 참고)
    admin       관리자                       Admin!2345  (.env SEED_ADMIN_*)
    202200001   학생 ACTIVE                  Student!234  ← 주 시연 계정
    202200002   학생 ACTIVE                  Student!234  ← 동시 예약·타인 예약 시연
    202200003   학생 PENDING (이메일 미인증)  Student!234  ← US-02 AC3 시연
    202200004   학생 ACTIVE + 이용 제한 3일   Student!234  ← US-05 AC4 시연
"""

import sys
from datetime import timedelta

from sqlalchemy import select

from app.core.clock import Clock
from app.core.config import get_settings
from app.core.database import SessionLocal
from app.core.security import hash_password
from app.models import (
    AccountStatus,
    OperationPolicy,
    RestrictionSource,
    Role,
    Seat,
    User,
    UserRestriction,
)

ROWS, COLS = "ABCD", 10
DEMO_PASSWORD = "Student!234"
STUDENTS = [
    ("202200001", "student1@example.ac.kr", "데모1", AccountStatus.ACTIVE),
    ("202200002", "student2@example.ac.kr", "데모2", AccountStatus.ACTIVE),
    ("202200003", "student3@example.ac.kr", "미인증", AccountStatus.PENDING),
    ("202200004", "student4@example.ac.kr", "제한중", AccountStatus.ACTIVE),
]
RESTRICTED_STUDENT = "202200004"


def run():
    s = get_settings()
    now = Clock().now()
    with SessionLocal() as db:
        existing_policy = db.get(OperationPolicy, 1)
        if existing_policy is not None and "--reset-policy" in sys.argv:
            db.delete(existing_policy)
            db.flush()
            existing_policy = None
        if existing_policy is None:
            db.add(OperationPolicy(id=1))

        existing = set(db.scalars(select(Seat.seat_number)))
        for r, row in enumerate(ROWS, start=1):
            for c in range(1, COLS + 1):
                num = f"{row}-{c:02d}"
                if num not in existing:
                    db.add(Seat(seat_number=num, grid_row=r, grid_col=c, enabled=True))

        def ensure_user(login_id, **kw) -> User:
            user = db.scalar(select(User).where(User.login_id == login_id))
            if user is None:
                user = User(login_id=login_id, **kw)
                db.add(user)
                db.flush()
            return user

        ensure_user(
            s.seed_admin_login_id,
            password_hash=hash_password(s.seed_admin_password),
            role=Role.ROLE_ADMIN,
            account_status=AccountStatus.ACTIVE,
            name="관리자",
        )
        for no, email, name, status in STUDENTS:
            user = ensure_user(
                no,
                student_no=no,
                email=email,
                name=name,
                password_hash=hash_password(DEMO_PASSWORD),
                role=Role.ROLE_STUDENT,
                account_status=status,
            )
            if no == RESTRICTED_STUDENT:
                # 데모 당일에도 제한 상태가 유지되도록 '지금부터 3일'로 매번 갱신
                db.query(UserRestriction).filter_by(user_id=user.id, released_at=None).delete()
                db.add(
                    UserRestriction(
                        user_id=user.id,
                        source=RestrictionSource.ADMIN,
                        starts_at=now,
                        ends_at=now + timedelta(days=3),
                        reason="데모용 이용 제한",
                    )
                )
        db.commit()

    print("seed done")
    with SessionLocal() as db:
        p = db.get(OperationPolicy, 1)
        mode = "시험 기간" if p.exam_mode else "평상시"
        print(
            f"  policy: 운영 {p.open_hour:02d}:00~{p.close_hour:02d}:00 · {p.slot_minutes}분 단위"
        )
        print(f"          {mode} +{p.days_ahead}일 · 최대 {p.max_hours}시간")
        if (p.open_hour, p.close_hour, p.slot_minutes) != (6, 23, 30):
            print("  ⚠️ 운영 정책이 기본값(06~23시·30분)과 다릅니다")
            print("     → python -m scripts.seed --reset-policy")
    print(f"  seats: {len(ROWS) * COLS}  admin: {s.seed_admin_login_id} / {s.seed_admin_password}")
    for no, _, name, status in STUDENTS:
        print(f"  {no} ({name}, {status.value}) / {DEMO_PASSWORD}")


if __name__ == "__main__":
    run()
