"""US-19 이용 종료(퇴실) 및 좌석 반환 — 설계서 checkout·D-01, Backlog v1.2.0 (Must / 2 SP) · D-47"""

import pytest

from app.models import ReservationStatus

pending = pytest.mark.skip(reason="US-19 구현 전 — 구현 후 이 데코레이터를 지우세요")

GRID = {"start_at": "2026-11-20T10:00:00", "end_at": "2026-11-20T12:00:00"}


def _checkout(client, headers, rid):
    return client.post(f"/api/reservations/{rid}/checkout", headers=headers)


@pending
def test_us19_ac1_checkout_completes_and_frees_seat(
    client, clock, policy, seats, make_user, auth_headers, make_reservation
):
    """Given 본인 CHECKED_IN When 퇴실 Then COMPLETED + 퇴실 시각, 좌석 즉시 예약 가능"""
    me = make_user("202200001")
    r = make_reservation(me, seats[0], "10:00", "12:00", status=ReservationStatus.CHECKED_IN)
    clock.advance(hours=2)  # 11:00
    res = _checkout(client, auth_headers(me), r.id)
    assert res.status_code == 200
    assert res.json()["status"] == "COMPLETED" and res.json()["ended_at"] == "2026-11-20T11:00:00"
    grid = client.get("/api/seats", params=GRID, headers=auth_headers(make_user("202200002")))
    assert grid.json()["seats"][0]["status"] == "AVAILABLE"


@pending
@pytest.mark.parametrize(
    "status",
    [
        ReservationStatus.RESERVED,
        ReservationStatus.CANCELLED,
        ReservationStatus.AUTO_CANCELLED,
        ReservationStatus.COMPLETED,
    ],
)
def test_us19_ac2_not_checked_in_rejected(
    client, policy, seats, make_user, auth_headers, make_reservation, status
):
    """Given 체크인 전·취소·자동 취소·이용 완료 When 퇴실 Then 거부 + 안내"""
    me = make_user()
    r = make_reservation(me, seats[0], "10:00", "12:00", status=status)
    res = _checkout(client, auth_headers(me), r.id)
    assert res.status_code == 409 and res.json()["code"] == "NOT_CHECKOUTABLE"


@pending
def test_us19_ac3_other_students_reservation_forbidden(
    client, policy, seats, make_user, auth_headers, make_reservation
):
    owner, other = make_user("202200001"), make_user("202200002")
    r = make_reservation(owner, seats[0], "10:00", "12:00", status=ReservationStatus.CHECKED_IN)
    res = _checkout(client, auth_headers(other), r.id)
    assert res.status_code == 403 and res.json()["code"] == "NOT_OWNER"


@pending
def test_us19_ac4_no_penalty(
    client, db_session, policy, seats, make_user, auth_headers, make_reservation
):
    """Given 퇴실 완료 When 패널티 확인 Then 노쇼 카운터 불변"""
    me = make_user()
    r = make_reservation(me, seats[0], "10:00", "12:00", status=ReservationStatus.CHECKED_IN)
    _checkout(client, auth_headers(me), r.id)
    db_session.refresh(me)
    assert me.no_show_count == 0
