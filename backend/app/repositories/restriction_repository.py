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


# ───────────────────────── Sprint 2 (스켈레톤 — 담당자가 구현) ─────────────────────────


def list_active(db: Session, user_id: int, now: datetime) -> list[UserRestriction]:
    """US-10·14: 지금 활성인 제한 전체 (D-17 연장 판단, 관리자 해제 시 전부 released_at 기록)."""
    raise NotImplementedError("US-10/14 list_active")


def add(db: Session, restriction: UserRestriction) -> UserRestriction:
    """US-10·14: 제한 이력 추가 (삭제하지 않고 이력으로 남긴다, D-51)."""
    raise NotImplementedError("US-10/14 add")
