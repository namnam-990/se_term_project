"""Seat 조회·잠금 — US-04·05."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Seat


def list_enabled(db: Session) -> list[Seat]:
    """US-04: 그리드 표시용 운영 좌석 전체 (행·열 순)."""
    return list(
        db.scalars(
            select(Seat).where(Seat.enabled.is_(True)).order_by(Seat.grid_row, Seat.grid_col)
        )
    )


def lock_by_id(db: Session, seat_id: int) -> Seat | None:
    """US-05 Core Flow 1: 좌석 행 FOR UPDATE (같은 좌석 동시 예약 직렬화, 명세서 4.4)."""
    return db.scalar(
        select(Seat)
        .where(Seat.id == seat_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
