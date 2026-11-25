"""US-17 관리자 권한 부여·회수 — FR-A-13 (Could / 2 SP) · D-46"""

import pytest

from app.models import Role

pending = pytest.mark.skip(reason="US-17 구현 전 (Could) — 구현 후 이 데코레이터를 지우세요")


def _role(client, headers, user_id, role):
    return client.put(f"/api/admin/users/{user_id}/role", json={"role": role}, headers=headers)


@pending
def test_us17_ac1_grant_admin(client, policy, make_user, auth_headers):
    admin = make_user("admin", role=Role.ROLE_ADMIN)
    student = make_user("202200001")
    res = _role(client, auth_headers(admin), student.id, "ROLE_ADMIN")
    assert res.status_code == 200 and res.json()["role"] == "ROLE_ADMIN"


@pending
def test_us17_ac2_revoke_other_admin(client, policy, make_user, auth_headers):
    """권한은 요청마다 DB에서 확인 → 회수 즉시 관리자 기능 차단 (D-46)"""
    admin = make_user("admin", role=Role.ROLE_ADMIN)
    other = make_user("admin2", role=Role.ROLE_ADMIN)
    other_headers = auth_headers(other)
    assert _role(client, auth_headers(admin), other.id, "ROLE_STUDENT").status_code == 200
    assert client.get("/api/admin/dashboard", headers=other_headers).status_code == 403


@pending
def test_us17_ac3_cannot_revoke_self(client, policy, make_user, auth_headers):
    admin = make_user("admin", role=Role.ROLE_ADMIN)
    res = _role(client, auth_headers(admin), admin.id, "ROLE_STUDENT")
    assert res.status_code == 400 and res.json()["code"] == "CANNOT_CHANGE_OWN_ROLE"
