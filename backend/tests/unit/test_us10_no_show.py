"""US-10 15분 미체크인 자동 취소 + 노쇼 3회 이상 자동 이용 제한 — FR-C-04, FR-X-10~13 (Must / 8 SP)

결정: D-17(개정)·D-34·D-36·D-37. 스케줄러 없이 NoShowService.run()을 FixedClock으로 직접
  호출 (명세서 4.2).
기준 날짜 2026-11-20, 예약 10:00~12:00 → 마감 10:15.
"""

from datetime import datetime, timedelta

import pytest
from sqlalchemy import func, select

from app.models import (
    CancelOrigin,
    NoShowEvent,
    ReservationStatus,
    RestrictionSource,
    UserRestriction,
)
from app.repositories.restriction_repository import find_active
from app.services.no_show_service import NoShowService

pending = pytest.mark.skip(reason="US-10 구현 전 — 구현 후 이 데코레이터를 지우세요")

GRID = {"start_at": "2026-11-20T10:00:00", "end_at": "2026-11-20T12:00:00"}


def _run(db_session, clock) -> int:
    return NoShowService(db_session, clock).run()


def _at(h: int, m: int, day: int = 20) -> datetime:
    return datetime(2026, 11, day, h, m)


def _move_to(clock, when: datetime) -> None:
    clock.advance(seconds=(when - clock.now()).total_seconds())


def _events(db_session, user_id) -> int:
    return db_session.scalar(
        select(func.count()).select_from(NoShowEvent).where(NoShowEvent.user_id == user_id)
    )


@pending
def test_us10_ac1_auto_cancel_after_15_minutes(
    client, clock, db_session, policy, seats, make_user, auth_headers, make_reservation
):
    """Given 15분 경과 미체크인 When 10분 주기 작업 Then AUTO_CANCELLED, 좌석 가용, 노쇼 +1"""
    me, other = make_user("202200001"), make_user("202200002")
    r = make_reservation(me, seats[0], "10:00", "12:00")

    _move_to(clock, _at(10, 14))  # 마감 1분 전 → 처리 안 함
    assert _run(db_session, clock) == 0

    _move_to(clock, _at(10, 15))  # 마감 정각 → 처리 (D-14·D-32 경계)
    assert _run(db_session, clock) == 1
    db_session.refresh(r)
    db_session.refresh(me)
    assert r.status == ReservationStatus.AUTO_CANCELLED
    assert r.cancel_origin == CancelOrigin.SYSTEM and r.penalty_applied is True
    assert me.no_show_count == 1 and _events(db_session, me.id) == 1
    grid = client.get("/api/seats", params=GRID, headers=auth_headers(other)).json()
    assert grid["seats"][0]["status"] == "AVAILABLE"  # FR-X-13 즉시 가용


@pending
def test_us10_run_twice_counts_once(clock, db_session, policy, seats, make_user, make_reservation):
    """설계서: 재실행해도 이중 집계 없음 (NoShowEvent.reservation_id UNIQUE + 재확인)"""
    me = make_user()
    make_reservation(me, seats[0], "10:00", "12:00")
    _move_to(clock, _at(10, 20))
    assert _run(db_session, clock) == 1
    assert _run(db_session, clock) == 0
    db_session.refresh(me)
    assert me.no_show_count == 1


@pending
def test_us10_checked_in_or_cancelled_not_processed(
    clock, db_session, policy, seats, make_user, make_reservation
):
    me = make_user()
    a = make_reservation(me, seats[0], "10:00", "12:00", status=ReservationStatus.CHECKED_IN)
    b = make_reservation(me, seats[1], "13:00", "14:00", status=ReservationStatus.CANCELLED)
    _move_to(clock, _at(14, 0))
    assert _run(db_session, clock) == 0
    db_session.refresh(a)
    db_session.refresh(b)
    assert (a.status, b.status) == (ReservationStatus.CHECKED_IN, ReservationStatus.CANCELLED)


@pending
def test_us10_ac2_third_no_show_restricts_3_days(
    clock, db_session, policy, seats, make_user, make_reservation
):
    """Given 누적 3회 이상 When 노쇼 처리 Then 즉시 이용 제한, 기간 3일 (처리 시각 기준)"""
    me = make_user()
    me.no_show_count = 2
    db_session.commit()
    make_reservation(me, seats[0], "10:00", "12:00")
    _move_to(clock, _at(10, 20))
    _run(db_session, clock)
    active = find_active(db_session, me.id, clock.now())
    assert active is not None and active.source == RestrictionSource.AUTO_NO_SHOW
    assert active.ends_at == _at(10, 20) + timedelta(days=3)


@pending
def test_us10_second_no_show_does_not_restrict(
    clock, db_session, policy, seats, make_user, make_reservation
):
    me = make_user()
    me.no_show_count = 1
    db_session.commit()
    make_reservation(me, seats[0], "10:00", "12:00")
    _move_to(clock, _at(10, 20))
    _run(db_session, clock)
    assert find_active(db_session, me.id, clock.now()) is None


@pending
def test_us10_every_no_show_after_third_restricts_again(
    clock, db_session, policy, seats, make_user, make_reservation
):
    """D-17(개정): 3회째부터 노쇼마다 3일. 카운터는 3에서 멈추지 않음 (FR-X-11)"""
    me = make_user()
    me.no_show_count = 3
    db_session.commit()
    make_reservation(me, seats[0], "10:00", "12:00", day=21)
    _move_to(clock, _at(10, 20, day=21))
    _run(db_session, clock)
    db_session.refresh(me)
    assert me.no_show_count == 4
    assert find_active(db_session, me.id, clock.now()).ends_at == _at(10, 20, day=24)


@pending
def test_us10_longer_existing_restriction_is_not_shortened(
    clock, db_session, policy, seats, make_user, make_reservation
):
    """D-17(개정): 이미 제한 중이면 종료일 = max(기존, 지금+3일)"""
    me = make_user()
    me.no_show_count = 2
    db_session.add(
        UserRestriction(
            user_id=me.id,
            source=RestrictionSource.ADMIN,
            starts_at=clock.now(),
            ends_at=clock.now() + timedelta(days=7),
        )
    )
    db_session.commit()
    make_reservation(me, seats[0], "10:00", "12:00")
    _move_to(clock, _at(10, 20))
    _run(db_session, clock)
    assert find_active(db_session, me.id, clock.now()).ends_at == datetime(2026, 11, 27, 9, 0)


@pending
def test_us10_ac3_restriction_released_after_3_days_count_kept(
    clock, db_session, policy, seats, make_user, make_reservation
):
    """Given 3일 경과 When 확인 Then 자동 해제. 자동 해제는 카운터를 0으로 만들지 않음 (D-17)"""
    me = make_user()
    me.no_show_count = 2
    db_session.commit()
    make_reservation(me, seats[0], "10:00", "12:00")
    _move_to(clock, _at(10, 20))
    _run(db_session, clock)
    ends = find_active(db_session, me.id, clock.now()).ends_at
    assert find_active(db_session, me.id, ends - timedelta(minutes=1)) is not None
    assert find_active(db_session, me.id, ends) is None  # AC4 경계: 정각에 해제
    db_session.refresh(me)
    assert me.no_show_count == 3
