"""US-12 실시간 대시보드 (지표 + 축소 그리드 3상태) — FR-A-01·02 (Must / 3 SP) · D-14·D-34·D-42

기준 시각 = 지금(clock). 좌석 A-01~A-04, 2026-11-20.
"""

import pytest

from app.models import ReservationStatus, Role

pending = pytest.mark.skip(reason="US-12 구현 전 — 구현 후 이 데코레이터를 지우세요")


@pytest.fixture
def admin_headers(make_user, auth_headers):
    return auth_headers(make_user("admin", role=Role.ROLE_ADMIN))


def _dashboard(client, headers):
    return client.get("/api/admin/dashboard", headers=headers).json()


def _statuses(body) -> dict[str, str]:
    return {s["seat_number"]: s["status"] for s in body["seats"]}


@pending
def test_us12_ac1_ac2_metrics_and_three_state_grid(
    client, clock, policy, seats, make_user, make_reservation, admin_headers
):
    """Given 사용 중 1 · 체크인 대기 1 · 시작 전 예약 1 When 대시보드 Then 지표와 3상태 그리드"""
    a, b, c = make_user("202200001"), make_user("202200002"), make_user("202200003")
    make_reservation(a, seats[0], "10:00", "12:00", status=ReservationStatus.CHECKED_IN)
    make_reservation(b, seats[1], "10:00", "12:00")  # 시작 후 5분 → 체크인 대기
    make_reservation(c, seats[2], "11:00", "13:00")  # 아직 시작 전 → 빈 좌석
    clock.advance(hours=1, minutes=5)  # 10:05
    body = _dashboard(client, admin_headers)
    assert (body["total_seats"], body["in_use"], body["waiting"], body["remaining"]) == (4, 1, 1, 2)
    assert body["utilization_rate"] == 25.0  # 사용 중 ÷ 운영 좌석 × 100 (설계서 5장)
    assert _statuses(body) == {
        "A-01": "IN_USE",
        "A-02": "WAITING",
        "A-03": "EMPTY",
        "A-04": "EMPTY",
    }


@pending
def test_us12_overdue_reserved_still_waiting_until_auto_cancel(
    client, clock, policy, seats, make_user, make_reservation, admin_headers
):
    """D-34·D-14 보완: 마감 지났지만 스케줄러가 아직 처리 안 한 RESERVED도 '체크인 대기'"""
    make_reservation(make_user(), seats[0], "10:00", "12:00")
    clock.advance(hours=1, minutes=20)  # 10:20
    assert _statuses(_dashboard(client, admin_headers))["A-01"] == "WAITING"


@pending
def test_us12_ac3_reflects_changes_after_refresh(
    client, clock, db_session, policy, seats, make_user, make_reservation, admin_headers
):
    """Given 체크인으로 상태 변경 When 다시 조회 Then 지표·그리드 일치"""
    r = make_reservation(make_user(), seats[0], "10:00", "12:00")
    clock.advance(hours=1, minutes=5)
    assert _dashboard(client, admin_headers)["waiting"] == 1
    r.status = ReservationStatus.CHECKED_IN
    db_session.commit()
    body = _dashboard(client, admin_headers)
    assert (body["in_use"], body["waiting"], body["remaining"]) == (1, 0, 3)


@pending
def test_us12_no_seats_rate_zero(client, policy, admin_headers):
    """설계서 5장: 운영 좌석 0석이면 0%"""
    body = _dashboard(client, admin_headers)
    assert body["total_seats"] == 0 and body["utilization_rate"] == 0.0


def test_us12_student_forbidden(client, policy, make_user, auth_headers):
    res = client.get("/api/admin/dashboard", headers=auth_headers(make_user()))
    assert res.status_code == 403 and res.json()["code"] == "FORBIDDEN_ROLE"
