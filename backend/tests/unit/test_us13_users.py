"""US-13 전체 학생 목록·학번/좌석번호 검색 — FR-A-10 (Must / 2 SP) · D-38·D-43"""

import pytest

from app.models import Role

pending = pytest.mark.skip(reason="US-13 구현 전 — 구현 후 이 데코레이터를 지우세요")


@pytest.fixture
def admin_headers(make_user, auth_headers):
    return auth_headers(make_user("admin", role=Role.ROLE_ADMIN))


def _users(client, headers, **params):
    return client.get("/api/admin/users", params=params, headers=headers)


@pending
def test_us13_ac1_list_all_students(client, policy, make_user, admin_headers):
    """Given 관리자 When 전체 목록 Then 학번·이메일·계정 상태·노쇼 횟수·제한 여부 (관리자
    계정 제외)"""
    make_user("202200001")
    make_user("202200002")
    items = _users(client, admin_headers).json()["items"]
    assert [i["student_no"] for i in items] == ["202200001", "202200002"]
    first = items[0]
    for key in ("email", "account_status", "no_show_count", "restricted_until", "reservations"):
        assert key in first


@pending
def test_us13_ac2_search_by_student_no(client, policy, make_user, admin_headers):
    make_user("202200001")
    make_user("202200002")
    items = _users(client, admin_headers, student_no="202200002").json()["items"]
    assert [i["student_no"] for i in items] == ["202200002"]


@pending
def test_us13_ac2_search_by_seat_number(
    client, clock, policy, seats, make_user, make_reservation, admin_headers
):
    """D-43: 그 좌석을 지금 점유 중이거나 오늘 남은 예약이 있는 학생. D-38: 예약 목록 포함"""
    me = make_user("202200001")
    make_user("202200002")
    r = make_reservation(me, seats[0], "10:00", "12:00")
    clock.advance(hours=1, minutes=5)
    items = _users(client, admin_headers, seat_number="A-01").json()["items"]
    assert [i["student_no"] for i in items] == ["202200001"]
    assert items[0]["reservations"][0]["id"] == r.id


@pending
def test_us13_ac3_no_result_message(client, policy, make_user, admin_headers):
    """Given 없는 학번 When 검색 Then 오류 없이 '결과 없음' 안내"""
    make_user("202200001")
    res = _users(client, admin_headers, student_no="209999999")
    assert res.status_code == 200
    assert res.json()["items"] == [] and res.json()["message"]
