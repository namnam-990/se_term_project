"""UserRestriction 조회 — US-05 AC4 (FR-R-12). 생성(노쇼·관리자)은 Sprint 2."""

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import UserRestriction


def find_active(db: Session, user_id: int, now: datetime) -> UserRestriction | None:
    """활성 제한 = starts_at <= now < ends_at AND released_at IS NULL.

    여러 개면 가장 늦게 끝나는 것을 반환 (해제일 안내용).
    """
    return db.scalar(
        select(UserRestriction)
        .where(
            UserRestriction.user_id == user_id,
            UserRestriction.starts_at <= now,
            UserRestriction.ends_at > now,
            UserRestriction.released_at.is_(None),
        )
        .order_by(UserRestriction.ends_at.desc())
        .limit(1)
    )
