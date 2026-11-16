"""US-06 본인 예약 내역 조회 및 상태별 필터링 — FR-R-20(필수) · FR-R-21(권장) (Must / 3 SP, D-21)"""

import pytest

from app.models import ReservationStatus

pending = pytest.mark.skip(reason="US-06 구현 전 — 구현 후 이 데코레이터를 지우세요")


@pending
def test_us06_ac1_only_mine_latest_first(client, seats, make_user, auth_headers, make_reservation):
    """Given 내 예약 여러 건 + 타인 예약 When 조회 Then 내 것만 최신순"""
    me, other = make_user("202200001"), make_user("202200002")
    make_reservation(me, seats[0], "10:00", "11:00", day=21)
    make_reservation(me, seats[0], "10:00", "11:00", ReservationStatus.CANCELLED, day=22)
    make_reservation(other, seats[1], "10:00", "11:00", day=23)

    items = client.get("/api/me/reservations", headers=auth_headers(me)).json()["items"]
    assert [i["start_at"][:10] for i in items] == ["2026-11-22", "2026-11-21"]


@pending
def test_us06_ac2_filter_by_status(client, seats, make_user, auth_headers, make_reservation):
    """Given 여러 상태 When status=CANCELLED Then 취소된 것만 (권장, FR-R-21)"""
    me = make_user()
    make_reservation(me, seats[0], "10:00", "11:00", day=21)
    make_reservation(me, seats[0], "10:00", "11:00", ReservationStatus.CANCELLED, day=22)
    items = client.get(
        "/api/me/reservations", params={"status": "CANCELLED"}, headers=auth_headers(me)
    ).json()["items"]
    assert len(items) == 1 and items[0]["status"] == "CANCELLED"


@pending
def test_us06_ac3_empty_history_message(client, make_user, auth_headers):
    """Given 이력 없음 When 조회 Then 오류 없이 안내 문구"""
    res = client.get("/api/me/reservations", headers=auth_headers(make_user()))
    assert res.status_code == 200
    assert res.json()["items"] == [] and res.json()["message"]
