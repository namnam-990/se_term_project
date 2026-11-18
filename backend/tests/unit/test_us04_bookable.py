"""US-04 AC3 / D-28 — 조회한 구간을 예약할 수 있는지 화면에 알려 주는 bookable·notice.

조회는 진행 중 시간대까지 보여주지만(현황 확인), 그대로 예약할 수 없으면 이유를 함께 내려준다.
판정은 예약 규칙(validate_booking)을 재사용하므로, 안내와 실제 예약 결과가 항상 같다.
"""


def _grid(client, headers, start, end):
    return client.get("/api/seats", params={"start_at": start, "end_at": end}, headers=headers)


def test_future_slot_is_bookable(client, policy, seats, make_user, auth_headers):
    body = _grid(
        client, auth_headers(make_user()), "2026-11-20T10:00:00", "2026-11-20T12:00:00"
    ).json()
    assert body["bookable"] is True and body["notice"] is None


def test_in_progress_slot_viewable_but_not_bookable(
    client, clock, policy, seats, make_user, auth_headers
):
    """10:15에 10~11시 조회 → 200(현황 확인) + 예약 불가 안내"""
    clock.advance(hours=1, minutes=15)
    res = _grid(client, auth_headers(make_user()), "2026-11-20T10:00:00", "2026-11-20T11:00:00")
    assert res.status_code == 200
    assert res.json()["bookable"] is False
    assert "지난 시간" in res.json()["notice"]


def test_too_long_range_viewable_but_not_bookable(client, policy, seats, make_user, auth_headers):
    """09~22시처럼 넓게 조회 → 현황은 보여주되 '최대 4시간' 안내"""
    res = _grid(client, auth_headers(make_user()), "2026-11-20T09:00:00", "2026-11-20T22:00:00")
    assert res.status_code == 200
    assert res.json()["bookable"] is False
    assert "최대 4시간" in res.json()["notice"]
