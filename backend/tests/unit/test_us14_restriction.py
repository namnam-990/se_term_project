"""US-14 이용 제한 수동 설정·해제 + 노쇼 초기화 — FR-A-11·12·21 (Must / 3 SP) · D-17·D-51"""

from datetime import timedelta

import pytest
from sqlalchemy import select

from app.models import CancelOrigin, NoShowEvent, RestrictionSource, Role, UserRestriction
from app.repositories.restriction_repository import find_active

pending = pytest.mark.skip(reason="US-14 구현 전 — 구현 후 이 데코레이터를 지우세요")

RESERVE = {"seat_id": None, "start_at": "2026-11-21T10:00:00", "end_at": "2026-11-21T12:00:00"}


@pytest.fixture
def admin_headers(make_user, auth_headers):
    return auth_headers(make_user("admin", role=Role.ROLE_ADMIN))


def _reserve(client, headers, seat_id):
    return client.post("/api/reservations", json={**RESERVE, "seat_id": seat_id}, headers=headers)


@pending
def test_us14_ac1_manual_restriction_blocks_until_date(
    client, policy, seats, make_user, auth_headers, admin_headers
):
    """Given 제한 일자 설정 When 적용 Then 즉시 제한, 그 날짜가 끝날 때까지 예약 차단 (D-51)"""
    me = make_user()
    res = client.put(
        f"/api/admin/users/{me.id}/restriction", json={"until": "2026-11-22"}, headers=admin_headers
    )
    assert res.status_code == 200
    assert res.json()["restricted_until"] == "2026-11-23T00:00:00"
    blocked = _reserve(client, auth_headers(me), seats[0].id)
    assert blocked.status_code == 403 and blocked.json()["code"] == "USER_RESTRICTED"


@pending
def test_us14_past_date_rejected(client, policy, make_user, admin_headers):
    me = make_user()
    res = client.put(
        f"/api/admin/users/{me.id}/restriction", json={"until": "2026-11-19"}, headers=admin_headers
    )
    assert res.status_code == 400 and res.json()["code"] == "INVALID_RESTRICTION_DATE"


@pending
def test_us14_ac2_release_allows_reservation(
    client, clock, db_session, policy, seats, make_user, auth_headers, admin_headers
):
    """Given 제한 중 When 해제 Then 즉시 예약 가능. 이력은 남음 (released_at)"""
    me = make_user()
    db_session.add(
        UserRestriction(
            user_id=me.id,
            source=RestrictionSource.AUTO_NO_SHOW,
            starts_at=clock.now(),
            ends_at=clock.now() + timedelta(days=3),
        )
    )
    db_session.commit()
    res = client.delete(f"/api/admin/users/{me.id}/restriction", headers=admin_headers)
    assert res.status_code == 200 and res.json()["restricted_until"] is None
    assert _reserve(client, auth_headers(me), seats[0].id).status_code == 200
    assert db_session.scalar(select(UserRestriction.released_at)) is not None


@pending
def test_us14_ac3_reset_no_show_count_keeps_history(
    client, clock, db_session, policy, seats, make_user, make_reservation, admin_headers
):
    """Given 노쇼 1회 이상 When 초기화 Then 횟수 0, 이력은 reset_at으로 보존 (설계서)"""
    me = make_user()
    r = make_reservation(me, seats[0], "10:00", "12:00")
    me.no_show_count = 2
    db_session.add(
        NoShowEvent(
            user_id=me.id, reservation_id=r.id, source=CancelOrigin.SYSTEM, occurred_at=clock.now()
        )
    )
    db_session.commit()
    res = client.post(f"/api/admin/users/{me.id}/no-shows/reset", headers=admin_headers)
    assert res.status_code == 200 and res.json()["no_show_count"] == 0
    assert db_session.scalar(select(NoShowEvent.reset_at)) is not None


@pending
def test_us14_reset_does_not_release_restriction(
    client, clock, db_session, policy, make_user, admin_headers
):
    """D-51·D-17: 초기화는 횟수만 0. 진행 중 제한은 별도 해제 기능으로"""
    me = make_user()
    me.no_show_count = 3
    db_session.add(
        UserRestriction(
            user_id=me.id,
            source=RestrictionSource.AUTO_NO_SHOW,
            starts_at=clock.now(),
            ends_at=clock.now() + timedelta(days=3),
        )
    )
    db_session.commit()
    client.post(f"/api/admin/users/{me.id}/no-shows/reset", headers=admin_headers)
    assert find_active(db_session, me.id, clock.now()) is not None
