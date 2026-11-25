"""US-08 예약 시작 15분 이내 QR 체크인 — FR-C-02·03 (Must / 5 SP) · D-30·D-32·D-51

체크인 요청은 '체크인 단말'(관리자 로그인 화면)이 보낸다 (D-30). 기준 날짜 2026-11-20, 예약
  10:00~12:00.
"""

from datetime import timedelta

import pytest

from app.models import ReservationStatus, RestrictionSource, Role, UserRestriction
from app.services.qr_service import qr_token

pending = pytest.mark.skip(reason="US-08 구현 전 — 구현 후 이 데코레이터를 지우세요")

GRID = {"start_at": "2026-11-20T10:00:00", "end_at": "2026-11-20T12:00:00"}


@pytest.fixture
def terminal(make_user, auth_headers):
    """체크인 단말 = 관리자 계정 로그인 (D-30)."""
    return auth_headers(make_user("admin", role=Role.ROLE_ADMIN))


def _check_in(client, headers, rid, token):
    return client.post(f"/api/reservations/{rid}/check-in", json={"token": token}, headers=headers)


@pending
def test_us08_ac1_check_in_within_15_minutes(
    client, clock, policy, seats, make_user, auth_headers, make_reservation, terminal
):
    """Given RESERVED + 시작 후 15분 이내 When QR 체크인 Then CHECKED_IN, 좌석 '사용 중'"""
    me, other = make_user("202200001"), make_user("202200002")
    r = make_reservation(me, seats[0], "10:00", "12:00")
    clock.advance(hours=1, minutes=5)  # 10:05
    res = _check_in(client, terminal, r.id, qr_token(r.id))
    assert res.status_code == 200
    assert res.json()["status"] == "CHECKED_IN" and res.json()["checked_in_at"]
    grid = client.get("/api/seats", params=GRID, headers=auth_headers(other)).json()
    assert grid["seats"][0]["status"] == "IN_USE"


@pending
@pytest.mark.parametrize("hm", [(1, 0), (1, 14)])  # 10:00, 10:14 → 허용
def test_us08_boundary_allowed(
    client, clock, policy, seats, make_user, make_reservation, terminal, hm
):
    r = make_reservation(make_user(), seats[0], "10:00", "12:00")
    clock.advance(hours=hm[0], minutes=hm[1])
    assert _check_in(client, terminal, r.id, qr_token(r.id)).status_code == 200


@pending
def test_us08_ac2_invalid_token_rejected(
    client, clock, policy, seats, make_user, make_reservation, terminal
):
    """Given 유효하지 않은 코드 When 체크인 Then 거부 + 안내"""
    r = make_reservation(make_user(), seats[0], "10:00", "12:00")
    clock.advance(hours=1, minutes=5)
    res = _check_in(client, terminal, r.id, "wrong-token")
    assert res.status_code == 400 and res.json()["code"] == "INVALID_QR"


@pending
def test_us08_ac2_already_checked_in_rejected(
    client, clock, policy, seats, make_user, make_reservation, terminal
):
    """Given 이미 체크인된 예약 When 다시 체크인 Then 거부"""
    r = make_reservation(make_user(), seats[0], "10:00", "12:00")
    clock.advance(hours=1, minutes=5)
    assert _check_in(client, terminal, r.id, qr_token(r.id)).status_code == 200
    res = _check_in(client, terminal, r.id, qr_token(r.id))
    assert res.status_code == 409 and res.json()["code"] == "ALREADY_CHECKED_IN"


@pending
@pytest.mark.parametrize("hm", [(0, 59), (1, 15)])  # 09:59 시작 전 / 10:15 마감 정각 (D-32)
def test_us08_ac3_outside_window_rejected(
    client, clock, policy, seats, make_user, make_reservation, terminal, hm
):
    """Given 시작 전 또는 15분 경과 When 체크인 Then 거부 + 체크인 가능 시간 안내"""
    r = make_reservation(make_user(), seats[0], "10:00", "12:00")
    clock.advance(hours=hm[0], minutes=hm[1])
    res = _check_in(client, terminal, r.id, qr_token(r.id))
    assert res.status_code == 409 and res.json()["code"] == "CHECKIN_WINDOW"


@pending
def test_us08_cancelled_reservation_rejected(
    client, clock, policy, seats, make_user, make_reservation, terminal
):
    r = make_reservation(
        make_user(), seats[0], "10:00", "12:00", status=ReservationStatus.CANCELLED
    )
    clock.advance(hours=1, minutes=5)
    res = _check_in(client, terminal, r.id, qr_token(r.id))
    assert res.status_code == 409 and res.json()["code"] == "RESERVATION_NOT_ACTIVE"


@pending
def test_us08_restricted_student_can_check_in_existing(
    client, clock, db_session, policy, seats, make_user, make_reservation, terminal
):
    """D-51: 이용 제한은 새 예약만 막는다 → 기존 예약 체크인은 허용"""
    me = make_user()
    r = make_reservation(me, seats[0], "10:00", "12:00")
    db_session.add(
        UserRestriction(
            user_id=me.id,
            source=RestrictionSource.AUTO_NO_SHOW,
            starts_at=clock.now(),
            ends_at=clock.now() + timedelta(days=3),
        )
    )
    db_session.commit()
    clock.advance(hours=1, minutes=5)
    assert _check_in(client, terminal, r.id, qr_token(r.id)).status_code == 200


def test_us08_student_cannot_call_terminal_api(
    client, clock, policy, seats, make_user, auth_headers, make_reservation
):
    """체크인 API는 단말(관리자)만 — 학생 직접 호출은 403 (권한 검사는 이미 동작)"""
    me = make_user()
    r = make_reservation(me, seats[0], "10:00", "12:00")
    res = _check_in(client, auth_headers(me), r.id, qr_token(r.id))
    assert res.status_code == 403 and res.json()["code"] == "FORBIDDEN_ROLE"
