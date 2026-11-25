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


# ───────────────────────── Sprint 2 (스켈레톤 — 담당자가 구현) ─────────────────────────


def find_no_show_candidates(db: Session, now: datetime, check_in_minutes: int) -> list[int]:
    """US-10: 노쇼 후보 예약 ID 목록.

    조건: status = RESERVED AND start_at + check_in_minutes ≤ now (D-14·D-32 마감과 같은 경계)
    - 잠그지 않고 ID만 가져온다. 실제 처리는 NoShowService가 건마다 회원 → 예약 잠금 후 다시
      확인 (D-36).
    - 서버가 꺼졌다 켜져도 밀린 건을 다음 실행에서 한꺼번에 처리한다.
    """
    raise NotImplementedError("US-10 find_no_show_candidates")


def list_active_at(db: Session, now: datetime) -> list[Reservation]:
    """US-12 대시보드: 지금 시점의 RESERVED·CHECKED_IN 예약 (시작 ≤ now < 종료).

    좌석별 3상태(D-42)와 지표 계산은 AdminDashboardService에서 한다.
    """
    raise NotImplementedError("US-12 list_active_at")


def list_current_and_upcoming_for_user(
    db: Session, user_id: int, now: datetime
) -> list[Reservation]:
    """US-13·D-38: 관리자 학생 목록에 함께 보여줄 예약 (종료 > now 인 RESERVED·CHECKED_IN,
    시작순)."""
    raise NotImplementedError("US-13 list_current_and_upcoming_for_user")


def list_checked_in_between(db: Session, start: datetime, end: datetime) -> list[Reservation]:
    """US-16 통계 (Could): 조회 구간과 겹치는 체크인 이력 (checked_in_at IS NOT NULL)."""
    raise NotImplementedError("US-16 list_checked_in_between")
