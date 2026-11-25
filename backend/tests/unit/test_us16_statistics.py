"""US-16 시간대별·날짜별 좌석 사용 통계 — FR-A-03 (Could / 2 SP)"""

from datetime import datetime

import pytest

from app.models import ReservationStatus, Role

pending = pytest.mark.skip(reason="US-16 구현 전 (Could) — 구현 후 이 데코레이터를 지우세요")


@pytest.fixture
def admin_headers(make_user, auth_headers):
    return auth_headers(make_user("admin", role=Role.ROLE_ADMIN))


def _stats(client, headers, start, end):
    return client.get("/api/admin/statistics", params={"from": start, "to": end}, headers=headers)


@pending
def test_us16_ac1_rate_for_used_day(
    client, db_session, policy, seats, make_user, make_reservation, admin_headers
):
    """Given 체크인 이력 When 기간 조회 Then 날짜별·시간대별 가동률(%)"""
    r = make_reservation(
        make_user(), seats[0], "10:00", "12:00", status=ReservationStatus.COMPLETED
    )
    r.checked_in_at = datetime(2026, 11, 20, 10, 0)
    r.ended_at = datetime(2026, 11, 20, 11, 0)
    db_session.commit()
    body = _stats(client, admin_headers, "2026-11-20", "2026-11-20").json()
    assert body["daily"][0]["utilization_rate"] > 0
    assert next(h for h in body["hourly"] if h["hour"] == 10)["utilization_rate"] > 0


@pending
def test_us16_ac2_invalid_period(client, policy, admin_headers):
    """Given 시작일 > 종료일 When 조회 Then 기간 설정 오류 안내"""
    res = _stats(client, admin_headers, "2026-11-21", "2026-11-20")
    assert res.status_code == 400 and res.json()["code"] == "INVALID_PERIOD"


@pending
def test_us16_ac3_no_data_is_zero(client, policy, seats, admin_headers):
    """Given 이용 기록 없음 When 조회 Then 오류 없이 0%"""
    body = _stats(client, admin_headers, "2026-11-20", "2026-11-21").json()
    assert all(d["utilization_rate"] == 0 for d in body["daily"])
