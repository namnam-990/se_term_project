"""US-05 가용 좌석 선택 및 시간대 지정 예약 생성 — FR-R-10 ~ 13 (Must / 8 SP)

동시 요청(AC2)의 진짜 검증은 MySQL 통합 테스트: tests/integration/test_us05_concurrency.py
"""

from datetime import datetime, timedelta

import pytest

from app.models import RestrictionSource, UserRestriction


def _reserve(client, headers, seat_id, start="10:00", end="12:00", day=20, key=None):
    body = {
        "seat_id": seat_id,
        "start_at": f"2026-11-{day:02d}T{start}:00",
        "end_at": f"2026-11-{day:02d}T{end}:00",
    }
    if key:
        body["request_key"] = key
    return client.post("/api/reservations", json=body, headers=headers)


def test_us05_ac1_reserve_success(client, policy, seats, make_user, auth_headers):
    """Given 제한 없음 + 가용 좌석 + 유효 시간 When 예약 Then RESERVED 저장 (FR-R-10·13)"""
    res = _reserve(client, auth_headers(make_user()), seats[0].id)
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "RESERVED" and body["seat_number"] == "A-01"


def test_us05_ac2_same_seat_second_request_conflict(client, policy, seats, make_user, auth_headers):
    """Given 이미 선택된 좌석 When 다른 학생 예약 Then 409 SEAT_ALREADY_RESERVED"""
    _reserve(client, auth_headers(make_user("202200001")), seats[0].id)
    res = _reserve(client, auth_headers(make_user("202200002")), seats[0].id, "11:00", "13:00")
    assert res.status_code == 409 and res.json()["code"] == "SEAT_ALREADY_RESERVED"


def test_us05_ac3_same_user_overlap_rejected(client, policy, seats, make_user, auth_headers):
    """Given 같은 시간대 예약 보유 When 다른 좌석 예약 Then 409 USER_TIME_OVERLAP (FR-R-11)"""
    h = auth_headers(make_user())
    _reserve(client, h, seats[0].id, "10:00", "12:00")
    res = _reserve(client, h, seats[1].id, "11:00", "13:00")
    assert res.status_code == 409 and res.json()["code"] == "USER_TIME_OVERLAP"


def test_us05_adjacent_slot_allowed(client, policy, seats, make_user, auth_headers):
    """경계값: 10~12시 다음 12~14시는 겹치지 않음 → 허용"""
    h = auth_headers(make_user())
    _reserve(client, h, seats[0].id, "10:00", "12:00")
    assert _reserve(client, h, seats[0].id, "12:00", "14:00").status_code == 200


def test_us05_ac4_restricted_user_rejected_with_release_date(
    client, db_session, clock, policy, seats, make_user, auth_headers
):
    """Given 이용 제한 중 When 예약 Then 403 USER_RESTRICTED + 해제일 안내 (FR-R-12)"""
    user = make_user()
    until = clock.now() + timedelta(days=3)
    db_session.add(
        UserRestriction(
            user_id=user.id, source=RestrictionSource.ADMIN, starts_at=clock.now(), ends_at=until
        )
    )
    db_session.commit()
    res = _reserve(client, auth_headers(user), seats[0].id)
    assert res.status_code == 403 and res.json()["code"] == "USER_RESTRICTED"
    assert datetime.fromisoformat(res.json()["restricted_until"]) == until


@pytest.mark.parametrize(
    "start,end,day,code",
    [
        ("10:00", "15:00", 20, "EXCEEDS_MAX_HOURS"),  # 5시간 > 4시간
        ("10:00", "12:00", 28, "OUT_OF_BOOKING_WINDOW"),  # 오늘+8일
        ("10:30", "12:00", 20, "INVALID_TIME_RANGE"),  # 60분 단위 아님
        ("21:00", "23:00", 20, "INVALID_TIME_RANGE"),  # 운영시간(22시) 밖
        ("12:00", "10:00", 20, "INVALID_TIME_RANGE"),  # 시작 >= 종료
    ],
    ids=["최대시간초과", "기간초과", "단위불일치", "운영시간밖", "역순"],
)
def test_us05_policy_validation(
    client, policy, seats, make_user, auth_headers, start, end, day, code
):
    """명세서 FR-A-20 정책 검증 — Backlog US-05 AC에는 없음 (D-25, D-11·12·13)"""
    res = _reserve(client, auth_headers(make_user()), seats[0].id, start, end, day)
    assert res.status_code == 400 and res.json()["code"] == code


def test_us05_exam_mode_max_3_hours(client, db_session, policy, seats, make_user, auth_headers):
    """시험 기간: 4시간 예약 → 400 (최대 3시간)"""
    policy.exam_mode = True
    db_session.commit()
    res = _reserve(client, auth_headers(make_user()), seats[0].id, "10:00", "14:00")
    assert res.status_code == 400 and res.json()["code"] == "EXCEEDS_MAX_HOURS"


def test_us05_same_request_key_not_duplicated(client, policy, seats, make_user, auth_headers):
    """더블 클릭 등 같은 요청 키 재전송 → 같은 예약 반환, 새로 만들지 않음"""
    h = auth_headers(make_user())
    a = _reserve(client, h, seats[0].id, key="k-123")
    b = _reserve(client, h, seats[0].id, key="k-123")
    assert a.status_code == b.status_code == 200
    assert a.json()["id"] == b.json()["id"]


def test_us05_unknown_seat_404(client, policy, seats, make_user, auth_headers):
    res = _reserve(client, auth_headers(make_user()), 9999)
    assert res.status_code == 404 and res.json()["code"] == "SEAT_NOT_FOUND"


def test_us05_timezone_aware_request_is_400_not_500(client, policy, seats, make_user, auth_headers):
    """시간대가 붙은 요청도 서버 오류 없이 400으로 안내"""
    body = {
        "seat_id": seats[0].id,
        "start_at": "2026-11-20T10:00:00+09:00",
        "end_at": "2026-11-20T12:00:00+09:00",
    }
    res = client.post("/api/reservations", json=body, headers=auth_headers(make_user()))
    assert res.status_code == 400 and res.json()["code"] == "INVALID_TIME_RANGE"
