"""US-09 학생 본인의 예약 직접 취소 및 좌석 반환 — FR-X-01 ~ 04 (Must / 3 SP)"""

import pytest

from app.models import Reservation, ReservationStatus, User

pending = pytest.mark.skip(reason="US-09 구현 전 — 구현 후 이 데코레이터를 지우세요")


def _cancel(client, headers, rid, reason="SCHEDULE_CHANGE"):
    return client.post(f"/api/reservations/{rid}/cancel", json={"reason": reason}, headers=headers)


@pending
def test_us09_ac1_cancel_frees_seat(
    client, policy, seats, make_user, auth_headers, make_reservation
):
    """Given RESERVED When 사유 선택 취소 Then CANCELLED + 좌석 즉시 '예약 가능' (FR-X-01·02·04)"""
    me = make_user()
    r = make_reservation(me, seats[0], "10:00", "12:00")
    h = auth_headers(me)
    res = _cancel(client, h, r.id)
    assert res.status_code == 200 and res.json()["status"] == "CANCELLED"
    grid = client.get(
        "/api/seats",
        params={"start_at": "2026-11-20T10:00:00", "end_at": "2026-11-20T12:00:00"},
        headers=h,
    ).json()
    assert grid["seats"][0]["status"] == "AVAILABLE"


@pending
def test_us09_ac1_cancel_during_checkin_wait(
    client, clock, seats, make_user, auth_headers, make_reservation
):
    """'체크인 대기'(시작 후 15분 이내 RESERVED)도 취소 가능 (FR-X-01, D-14)"""
    me = make_user()
    r = make_reservation(me, seats[0], "10:00", "12:00")
    clock.advance(hours=1, minutes=5)  # 10:05
    assert _cancel(client, auth_headers(me), r.id).status_code == 200


@pending
def test_us09_ac2_no_penalty(client, db_session, seats, make_user, auth_headers, make_reservation):
    """Given 직접 취소 When 패널티 확인 Then 노쇼 횟수 불변·패널티 없음 (FR-X-03)"""
    me = make_user()
    r = make_reservation(me, seats[0], "10:00", "12:00")
    _cancel(client, auth_headers(me), r.id)
    db_session.expire_all()
    assert db_session.get(User, me.id).no_show_count == 0
    saved = db_session.get(Reservation, r.id)
    assert saved.penalty_applied is False and saved.cancel_origin.value == "STUDENT"


@pending
@pytest.mark.parametrize("status", [ReservationStatus.CHECKED_IN, ReservationStatus.CANCELLED])
def test_us09_ac3_not_cancellable(client, seats, make_user, auth_headers, make_reservation, status):
    """Given 체크인 완료 또는 이미 취소 When 취소 Then 409 NOT_CANCELLABLE"""
    me = make_user()
    r = make_reservation(me, seats[0], "10:00", "12:00", status)
    res = _cancel(client, auth_headers(me), r.id)
    assert res.status_code == 409 and res.json()["code"] == "NOT_CANCELLABLE"


@pending
def test_us09_other_students_reservation_forbidden(
    client, seats, make_user, auth_headers, make_reservation
):
    """권한 오류: 타인 예약 취소 → 403 NOT_OWNER (US-02 AC2, 명세 4.5)"""
    owner, intruder = make_user("202200001"), make_user("202200002")
    r = make_reservation(owner, seats[0], "10:00", "12:00")
    res = _cancel(client, auth_headers(intruder), r.id)
    assert res.status_code == 403 and res.json()["code"] == "NOT_OWNER"


def test_us09_invalid_reason_rejected(client, make_user, auth_headers):
    """잘못된 사유 값 → 400 VALIDATION_ERROR (스키마 검증 — 이미 동작)"""
    res = _cancel(client, auth_headers(make_user()), 1, reason="BORED")
    assert res.status_code == 400 and res.json()["code"] == "VALIDATION_ERROR"
