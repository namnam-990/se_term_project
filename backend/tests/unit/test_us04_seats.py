"""US-04 날짜·시간대별 실시간 좌석 현황 조회 — FR-R-01 ~ 03 (Must / 3 SP, 기준 스토리)

※ FR-R-03(시험 기간 최대 시간 표시)은 Backlog에선 US-15지만 명세서 기준 좌석 조회에 포함 (D-06·D-22)
"""

import time

import pytest

from app.models import ReservationStatus

pending = pytest.mark.skip(reason="US-04 구현 전 — 구현 후 이 데코레이터를 지우세요")


def _grid(client, headers, start="2026-11-20T10:00:00", end="2026-11-20T12:00:00"):
    return client.get("/api/seats", params={"start_at": start, "end_at": end}, headers=headers)


@pending
def test_us04_ac1_four_states_within_500ms(
    client, policy, seats, make_user, auth_headers, make_reservation
):
    """Given 날짜·시간 선택 When 조회 Then 그리드 + 4상태, 500ms 이내 (FR-R-01·02, 명세 4.4)"""
    me, other = make_user("202200001"), make_user("202200002")
    make_reservation(me, seats[0], "10:00", "12:00")  # A-01 내 예약
    make_reservation(other, seats[1], "10:00", "12:00", ReservationStatus.CHECKED_IN)  # A-02
    make_reservation(other, seats[2], "11:00", "13:00")  # A-03 (부분 겹침)
    make_reservation(other, seats[3], "08:00", "09:00", ReservationStatus.CANCELLED)  # A-04

    t0 = time.perf_counter()
    res = _grid(client, auth_headers(me))
    elapsed = time.perf_counter() - t0

    assert res.status_code == 200
    status = {s["seat_number"]: s["status"] for s in res.json()["seats"]}
    assert status == {"A-01": "MINE", "A-02": "IN_USE", "A-03": "RESERVED", "A-04": "AVAILABLE"}
    assert elapsed < 0.5


@pending
def test_us04_ac2_other_timeslot_recomputed(
    client, policy, seats, make_user, auth_headers, make_reservation
):
    """Given 10~12시 예약 존재 When 12~14시 조회 Then 모두 '예약 가능' (경계 시각은 안 겹침)"""
    me = make_user("202200001")
    make_reservation(me, seats[0], "10:00", "12:00")
    res = _grid(client, auth_headers(me), "2026-11-20T12:00:00", "2026-11-20T14:00:00")
    assert {s["status"] for s in res.json()["seats"]} == {"AVAILABLE"}


@pending
@pytest.mark.parametrize(
    "start,end",
    [
        ("2026-11-19T10:00:00", "2026-11-19T12:00:00"),  # 어제 (과거)
        ("2026-11-28T10:00:00", "2026-11-28T12:00:00"),  # 오늘+8일 (평상시 +7일 초과)
    ],
    ids=["과거", "예약가능일수초과"],
)
def test_us04_ac3_out_of_window_rejected(
    client, policy, seats, make_user, auth_headers, start, end
):
    """Given 과거 또는 허용 일수 초과 When 조회 Then 400 OUT_OF_BOOKING_WINDOW + 안내 (D-13)"""
    res = _grid(client, auth_headers(make_user()), start, end)
    assert res.status_code == 400 and res.json()["code"] == "OUT_OF_BOOKING_WINDOW"


@pending
def test_us04_window_last_day_allowed(client, policy, seats, make_user, auth_headers):
    """경계값: 오늘+7일은 허용 (양 끝 포함, D-13)"""
    res = _grid(client, auth_headers(make_user()), "2026-11-27T10:00:00", "2026-11-27T12:00:00")
    assert res.status_code == 200


@pending
def test_us04_ac4_exam_mode_policy_shown(
    client, db_session, policy, seats, make_user, auth_headers
):
    """Given 시험 기간 When 조회 Then 응답에 최대 3시간·당일~다음 날 정책 포함 (FR-R-03)"""
    policy.exam_mode = True
    db_session.commit()
    body = _grid(client, auth_headers(make_user())).json()
    assert body["policy"]["exam_mode"] is True
    assert (body["policy"]["max_hours"], body["policy"]["days_ahead"]) == (3, 1)
