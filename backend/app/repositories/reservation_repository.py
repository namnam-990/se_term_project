"""Reservation 조회·저장 — US-04·05·06·09.

겹침 조건 (설계서 Data Integrity Rules):
    기존.start_at < 요청.end_at AND 기존.end_at > 요청.start_at
    AND 기존.status IN (RESERVED, CHECKED_IN)
경계: 10:00~12:00 과 12:00~14:00 은 겹치지 않음 (< , > 사용 — <= 쓰면 안 됨)
"""

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models import OCCUPYING_STATUSES, Reservation, ReservationStatus


def _overlap(start_at: datetime, end_at: datetime):
    return (
        Reservation.start_at < end_at,
        Reservation.end_at > start_at,
        Reservation.status.in_(OCCUPYING_STATUSES),
    )


def find_overlapping(db: Session, start_at: datetime, end_at: datetime) -> list[Reservation]:
    """US-04: 조회 구간과 겹치는 점유 예약 전체 → 좌석 4상태 계산용 (쿼리 1회)."""
    return list(db.scalars(select(Reservation).where(*_overlap(start_at, end_at))))


def exists_overlap_for_seat(
    db: Session, seat_id: int, start_at: datetime, end_at: datetime
) -> bool:
    """US-05 AC2: 같은 좌석 겹침 (좌석 잠금 '후'에 호출)."""
    q = select(Reservation.id).where(Reservation.seat_id == seat_id, *_overlap(start_at, end_at))
    return db.scalar(q.limit(1)) is not None


def exists_overlap_for_user(
    db: Session, user_id: int, start_at: datetime, end_at: datetime
) -> bool:
    """US-05 AC3 (FR-R-11): 같은 학생 같은 시간대 중복 (회원 잠금 '후'에 호출)."""
    q = select(Reservation.id).where(Reservation.user_id == user_id, *_overlap(start_at, end_at))
    return db.scalar(q.limit(1)) is not None


def find_by_request_key(db: Session, request_key: str) -> Reservation | None:
    """US-05: 같은 요청 재전송 시 기존 예약 반환."""
    return db.scalar(select(Reservation).where(Reservation.request_key == request_key))


def list_by_user(
    db: Session, user_id: int, status: ReservationStatus | None = None
) -> list[Reservation]:
    """US-06 (FR-R-20·21): 본인 것만, 최신순(시작 시각 내림차순), 상태 필터."""
    q = (
        select(Reservation)
        .options(joinedload(Reservation.seat))
        .where(Reservation.user_id == user_id)
    )
    if status is not None:
        q = q.where(Reservation.status == status)
    return list(db.scalars(q.order_by(Reservation.start_at.desc(), Reservation.id.desc())))


def lock_by_id(db: Session, reservation_id: int) -> Reservation | None:
    """US-09: 취소 대상 예약 FOR UPDATE (Sprint 2 체크인·자동취소와 경합 대비)."""
    return db.scalar(
        select(Reservation)
        .where(Reservation.id == reservation_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )


def add(db: Session, reservation: Reservation) -> Reservation:
    db.add(reservation)
    db.flush()
    return reservation
