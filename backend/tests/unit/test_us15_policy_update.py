"""US-15 시험 기간·평상시 정책 전환 — FR-R-03, FR-A-20, 명세서 4.1 (Must / 5 SP) · D-25·D-45

표시(FR-R-03)와 예약 검증(D-25)은 Sprint 1에서 완료 → 여기서는 관리자 '전환' 기능을 검증.
기준 시각 2026-11-20 09:00.
"""

import pytest

from app.models import ReservationStatus, Role

pending = pytest.mark.skip(reason="US-15 구현 전 — 구현 후 이 데코레이터를 지우세요")

NORMAL = {
    "exam_mode": False,
    "normal_days_ahead": 7,
    "normal_max_hours": 4,
    "exam_days_ahead": 1,
    "exam_max_hours": 3,
    "check_in_minutes": 15,
    "no_show_threshold": 3,
    "restriction_days": 3,
}


@pytest.fixture
def admin_headers(make_user, auth_headers):
    return auth_headers(make_user("admin", role=Role.ROLE_ADMIN))


def _put(client, headers, **changes):
    return client.put("/api/admin/policies/current", json={**NORMAL, **changes}, headers=headers)


def _reserve(client, headers, seat_id, day, start, end):
    body = {
        "seat_id": seat_id,
        "start_at": f"2026-11-{day}T{start}:00",
        "end_at": f"2026-11-{day}T{end}:00",
    }
    return client.post("/api/reservations", json=body, headers=headers)


@pending
def test_us15_ac1_exam_mode_on_limits_booking(
    client, policy, seats, make_user, auth_headers, admin_headers
):
    """Given 시험 기간 활성 When 조회·예약 Then 최대 3시간 표시, 당일~다음 날·3시간 제한"""
    assert _put(client, admin_headers, exam_mode=True).status_code == 200
    h = auth_headers(make_user())
    shown = client.get("/api/policies/current", headers=h).json()
    assert (shown["exam_mode"], shown["max_hours"], shown["days_ahead"]) == (True, 3, 1)
    too_far = _reserve(client, h, seats[0].id, 22, "10:00", "12:00")  # 모레
    assert too_far.json()["code"] == "OUT_OF_BOOKING_WINDOW"
    too_long = _reserve(client, h, seats[0].id, 21, "10:00", "14:00")  # 4시간
    assert too_long.json()["code"] == "EXCEEDS_MAX_HOURS"


@pending
def test_us15_ac2_back_to_normal_without_code_change(
    client, policy, seats, make_user, auth_headers, admin_headers
):
    """Given 평상시로 전환 When 예약 Then +7일·4시간 허용"""
    _put(client, admin_headers, exam_mode=True)
    _put(client, admin_headers, exam_mode=False)
    res = _reserve(client, auth_headers(make_user()), seats[0].id, 27, "10:00", "14:00")
    assert res.status_code == 200


@pending
def test_us15_existing_reservations_kept(
    client, db_session, policy, seats, make_user, make_reservation, admin_headers
):
    """D-45: 정책 변경은 새 예약부터 — 기존 예약은 소급 취소하지 않음"""
    r = make_reservation(make_user(), seats[0], "10:00", "14:00", day=25)
    _put(client, admin_headers, exam_mode=True)
    db_session.refresh(r)
    assert r.status == ReservationStatus.RESERVED


@pending
@pytest.mark.parametrize(
    "changes", [{"exam_max_hours": 0}, {"normal_days_ahead": -1}, {"check_in_minutes": 0}]
)
def test_us15_invalid_values_rejected(client, policy, admin_headers, changes):
    """D-45: 잘못된 값은 저장 전에 400"""
    assert _put(client, admin_headers, **changes).status_code == 400


def test_us15_invalid_values_rejected_by_schema(client, policy, admin_headers):
    """범위 검사는 PolicyUpdateRequest가 Service 전에 막는다 (지금도 동작)"""
    res = _put(client, admin_headers, exam_max_hours=0)
    assert res.status_code == 400 and res.json()["code"] == "VALIDATION_ERROR"


def test_us15_student_forbidden(client, policy, make_user, auth_headers):
    res = _put(client, auth_headers(make_user()))
    assert res.status_code == 403 and res.json()["code"] == "FORBIDDEN_ROLE"
