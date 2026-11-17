"""US-09 학생 본인의 예약 직접 취소 및 좌석 반환 — FR-X-01 ~ 04 (Must / 3 SP)"""

import pytest

from app.models import Reservation, ReservationStatus, User


def _cancel(client, headers, rid, reason="SCHEDULE_CHANGE"):
    return client.post(f"/api/reservations/{rid}/cancel", json={"reason": reason}, headers=headers)


def _reserve(client, headers, seat_id):
    body = {"seat_id": seat_id, "start_at": "2026-11-20T10:00:00", "end_at": "2026-11-20T12:00:00"}
    return client.post("/api/reservations", json=body, headers=headers)


def test_us09_ac1_cancel_frees_seat(
    client, policy, seats, make_user, auth_headers, make_reservation
):
    """Given RESERVED When 사유 선택 취소 Then CANCELLED + 좌석 즉시 '예약 가능' (FR-X-01·02·04)

    '즉시 가용'은 다른 학생이 같은 좌석·시간을 바로 예약할 수 있는지로 확인한다.
    (좌석 그리드 화면 확인은 US-04 구현 후 데모에서)
    """
    me, other = make_user("202200001"), make_user("202200002")
    r = make_reservation(me, seats[0], "10:00", "12:00")

    assert _reserve(client, auth_headers(other), seats[0].id).status_code == 409  # 취소 전: 점유
    res = _cancel(client, auth_headers(me), r.id)
    assert res.status_code == 200 and res.json()["status"] == "CANCELLED"
    assert res.json()["cancel_reason"] == "SCHEDULE_CHANGE"
    assert _reserve(client, auth_headers(other), seats[0].id).status_code == 200  # 취소 후: 가용


def test_us09_ac1_cancel_during_checkin_wait(
    client, clock, policy, seats, make_user, auth_headers, make_reservation
):
    """'체크인 대기'(시작 후 15분 이내 RESERVED)도 취소 가능 (FR-X-01, D-14)"""
    me = make_user()
    r = make_reservation(me, seats[0], "10:00", "12:00")
    clock.advance(hours=1, minutes=14)  # 10:14 — 마감 1분 전
    assert _cancel(client, auth_headers(me), r.id).status_code == 200


def test_us09_cancel_after_checkin_deadline_rejected(
    client, clock, policy, seats, make_user, auth_headers, make_reservation
):
    """경계값: 시작 + 15분(10:15)부터는 노쇼 확정 시점 → 취소 불가 (D-26)"""
    me = make_user()
    r = make_reservation(me, seats[0], "10:00", "12:00")
    clock.advance(hours=1, minutes=15)  # 10:15
    res = _cancel(client, auth_headers(me), r.id)
    assert res.status_code == 409 and res.json()["code"] == "NOT_CANCELLABLE"


def test_us09_ac2_no_penalty(
    client, db_session, policy, seats, make_user, auth_headers, make_reservation
):
    """Given 직접 취소 When 패널티 확인 Then 노쇼 횟수 불변·패널티 없음 (FR-X-03)"""
    me = make_user()
    r = make_reservation(me, seats[0], "10:00", "12:00")
    _cancel(client, auth_headers(me), r.id)
    db_session.expire_all()
    assert db_session.get(User, me.id).no_show_count == 0
    saved = db_session.get(Reservation, r.id)
    assert saved.penalty_applied is False
    assert saved.cancel_origin.value == "STUDENT"
    assert saved.cancelled_by == me.id and saved.cancelled_at is not None


@pytest.mark.parametrize("status", [ReservationStatus.CHECKED_IN, ReservationStatus.CANCELLED])
def test_us09_ac3_not_cancellable(
    client, policy, seats, make_user, auth_headers, make_reservation, status
):
    """Given 체크인 완료 또는 이미 취소 When 취소 Then 409 NOT_CANCELLABLE"""
    me = make_user()
    r = make_reservation(me, seats[0], "10:00", "12:00", status)
    res = _cancel(client, auth_headers(me), r.id)
    assert res.status_code == 409 and res.json()["code"] == "NOT_CANCELLABLE"


def test_us09_other_students_reservation_forbidden(
    client, policy, seats, make_user, auth_headers, make_reservation
):
    """권한 오류: 타인 예약 취소 → 403 NOT_OWNER, 예약은 그대로 (US-02 AC2, 명세 4.5)"""
    owner, intruder = make_user("202200001"), make_user("202200002")
    r = make_reservation(owner, seats[0], "10:00", "12:00")
    res = _cancel(client, auth_headers(intruder), r.id)
    assert res.status_code == 403 and res.json()["code"] == "NOT_OWNER"


def test_us09_unknown_reservation_404(client, policy, make_user, auth_headers):
    res = _cancel(client, auth_headers(make_user()), 9999)
    assert res.status_code == 404 and res.json()["code"] == "RESERVATION_NOT_FOUND"


def test_us09_invalid_reason_rejected(client, make_user, auth_headers):
    """잘못된 사유 값 → 400 VALIDATION_ERROR (스키마 검증)"""
    res = _cancel(client, auth_headers(make_user()), 1, reason="BORED")
    assert res.status_code == 400 and res.json()["code"] == "VALIDATION_ERROR"
