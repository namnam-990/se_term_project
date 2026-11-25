"""US-11 관리자 강제 취소 (사유·패널티) — FR-X-20~22 (Must / 3 SP) · D-39·D-40·D-41"""

import pytest
from sqlalchemy import select

from app.models import CancelOrigin, NoShowEvent, ReservationStatus, Role
from app.repositories.restriction_repository import find_active

pending = pytest.mark.skip(reason="US-11 구현 전 — 구현 후 이 데코레이터를 지우세요")

GRID = {"start_at": "2026-11-20T10:00:00", "end_at": "2026-11-20T12:00:00"}


@pytest.fixture
def admin_headers(make_user, auth_headers):
    return auth_headers(make_user("admin", role=Role.ROLE_ADMIN))


def _cancel(client, headers, rid, **body):
    return client.post(f"/api/admin/reservations/{rid}/cancel", json=body, headers=headers)


@pending
def test_us11_ac1_cancel_without_penalty(
    client, db_session, policy, seats, make_user, auth_headers, make_reservation, admin_headers
):
    """Given 사유 + 패널티 미부여 When 강제 취소 Then 취소, 사유 기록, 좌석 즉시 가용, 노쇼 없음"""
    me = make_user()
    r = make_reservation(me, seats[0], "10:00", "12:00")
    res = _cancel(client, admin_headers, r.id, reason="FACILITY_CHECK", apply_penalty=False)
    assert res.status_code == 200 and res.json()["status"] == "CANCELLED"
    db_session.refresh(r)
    db_session.refresh(me)
    assert r.cancel_origin == CancelOrigin.ADMIN and r.cancel_reason == "FACILITY_CHECK"
    assert r.penalty_applied is False and me.no_show_count == 0
    grid = client.get("/api/seats", params=GRID, headers=auth_headers(make_user("202200002")))
    assert grid.json()["seats"][0]["status"] == "AVAILABLE"


@pending
def test_us11_ac2_cancel_with_penalty(
    client, db_session, policy, seats, make_user, make_reservation, admin_headers
):
    """Given 사유 + 패널티 부여 When 강제 취소 Then 취소 + 노쇼 +1 (NoShowEvent source=ADMIN)"""
    me = make_user()
    r = make_reservation(me, seats[0], "10:00", "12:00")
    _cancel(client, admin_headers, r.id, reason="RULE_VIOLATION", apply_penalty=True)
    db_session.refresh(me)
    assert me.no_show_count == 1
    event = db_session.scalar(select(NoShowEvent).where(NoShowEvent.reservation_id == r.id))
    assert event.source == CancelOrigin.ADMIN


@pending
def test_us11_ac3_reason_required(
    client, policy, seats, make_user, make_reservation, admin_headers
):
    """Given 사유 없음 When 강제 취소 Then 거부 + 사유 필수 안내"""
    r = make_reservation(make_user(), seats[0], "10:00", "12:00")
    res = _cancel(client, admin_headers, r.id, apply_penalty=False)
    assert res.status_code == 400 and res.json()["code"] == "REASON_REQUIRED"


@pending
def test_us11_reason_and_penalty_are_independent(
    client, db_session, policy, seats, make_user, make_reservation, admin_headers
):
    """D-39: 시설 점검 사유라도 패널티 부여 가능 (명세 FR-X-22 '선택')"""
    me = make_user()
    r = make_reservation(me, seats[0], "10:00", "12:00")
    _cancel(client, admin_headers, r.id, reason="FACILITY_CHECK", apply_penalty=True)
    db_session.refresh(me)
    assert me.no_show_count == 1


@pending
def test_us11_checked_in_reservation_ends(
    client, db_session, policy, seats, make_user, make_reservation, admin_headers
):
    """D-40: 사용 중(CHECKED_IN)도 강제 취소 가능, ended_at 기록"""
    r = make_reservation(
        make_user(), seats[0], "10:00", "12:00", status=ReservationStatus.CHECKED_IN
    )
    res = _cancel(client, admin_headers, r.id, reason="SYSTEM_FIX", apply_penalty=False)
    assert res.status_code == 200 and res.json()["ended_at"]


@pending
def test_us11_penalty_can_trigger_restriction(
    client, clock, db_session, policy, seats, make_user, make_reservation, admin_headers
):
    """D-41: 관리자 패널티도 같은 규칙 — 카운터 3 이상이면 3일 제한"""
    me = make_user()
    me.no_show_count = 2
    db_session.commit()
    r = make_reservation(me, seats[0], "10:00", "12:00")
    _cancel(client, admin_headers, r.id, reason="RULE_VIOLATION", apply_penalty=True)
    assert find_active(db_session, me.id, clock.now()) is not None


@pending
def test_us11_cancelled_reservation_not_cancellable(
    client, policy, seats, make_user, make_reservation, admin_headers
):
    r = make_reservation(
        make_user(), seats[0], "10:00", "12:00", status=ReservationStatus.CANCELLED
    )
    res = _cancel(client, admin_headers, r.id, reason="OTHER", apply_penalty=False)
    assert res.status_code == 409 and res.json()["code"] == "NOT_CANCELLABLE"


def test_us11_student_forbidden(client, policy, seats, make_user, auth_headers, make_reservation):
    """관리자 전용 (권한 검사는 이미 동작)"""
    me = make_user()
    r = make_reservation(me, seats[0], "10:00", "12:00")
    res = _cancel(client, auth_headers(me), r.id, reason="OTHER", apply_penalty=False)
    assert res.status_code == 403 and res.json()["code"] == "FORBIDDEN_ROLE"
