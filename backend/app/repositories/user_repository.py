"""User 조회·저장·잠금 — US-01·02·03·05 공용.

Repository는 '어떻게 꺼내고 저장하는가'만 담당한다. 업무 판단(if …)은 Service에서.
"""

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models import User


def find_by_login_id(db: Session, login_id: str) -> User | None:
    """US-02: 학생은 학번, 관리자는 관리자 ID로 로그인 (FR-U-10)."""
    return db.scalar(select(User).where(User.login_id == login_id))


def exists_student_no_or_email(db: Session, student_no: str, email: str) -> tuple[bool, bool]:
    """US-01 AC4 (FR-U-06): (학번 중복 여부, 이메일 중복 여부)."""
    rows = db.execute(
        select(User.student_no, User.email).where(
            or_(User.student_no == student_no, User.email == email)
        )
    ).all()
    return any(r.student_no == student_no for r in rows), any(r.email == email for r in rows)


def find_by_email(db: Session, email: str) -> User | None:
    return db.scalar(select(User).where(User.email == email))


def get_by_id(db: Session, user_id: int) -> User | None:
    return db.get(User, user_id)


def lock_by_id(db: Session, user_id: int) -> User | None:
    """US-05 Core Flow 1: 회원 행 FOR UPDATE (같은 학생 동시 예약 직렬화)."""
    return db.scalar(
        select(User)
        .where(User.id == user_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )


def add(db: Session, user: User) -> User:
    db.add(user)
    db.flush()  # id 채우기
    return user
