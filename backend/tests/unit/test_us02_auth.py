"""US-02 로그인·로그아웃·역할별 접근 제어 — FR-U-10 ~ 12, 14 (Must / 5 SP)"""

import pytest

from app.models import AccountStatus, Role
from tests.conftest import DEFAULT_PASSWORD

pending = pytest.mark.skip(reason="US-02 구현 전 — 구현 후 이 데코레이터를 지우세요")


def _login(client, login_id, password=DEFAULT_PASSWORD):
    return client.post("/api/auth/login", json={"login_id": login_id, "password": password})


@pending
def test_us02_ac1_student_login_success(client, make_user):
    """Given ACTIVE 학생 + 맞는 비밀번호 When 로그인 Then 토큰 발급 (Access 1시간, 명세 4.5)"""
    make_user("202200001")
    res = _login(client, "202200001")
    assert res.status_code == 200
    body = res.json()
    assert body["access_token"] and body["role"] == "ROLE_STUDENT"
    assert body["expires_in"] == 3600
    assert "refresh_token" in client.cookies and "csrf_token" in client.cookies  # D-02·D-05


@pending
def test_us02_ac1_admin_login_with_admin_id(client, make_user):
    """FR-U-10: 관리자는 관리자 ID로 로그인"""
    make_user("admin", role=Role.ROLE_ADMIN)
    res = _login(client, "admin")
    assert res.status_code == 200 and res.json()["role"] == "ROLE_ADMIN"


@pending
def test_us02_wrong_password_does_not_reveal_which(client, make_user):
    """ID/비밀번호 중 무엇이 틀렸는지 노출하지 않음 → 같은 401 LOGIN_FAILED"""
    make_user("202200001")
    a = _login(client, "202200001", "Wrong!234")
    b = _login(client, "nobody", "Wrong!234")
    assert a.status_code == b.status_code == 401
    assert a.json()["code"] == b.json()["code"] == "LOGIN_FAILED"


def test_us02_ac2_admin_cannot_use_student_api(client, policy, make_user, auth_headers):
    """FR-U-12 역할 분리: 관리자 토큰으로 학생 전용 API → 403 FORBIDDEN_ROLE (이미 동작)

    학생→타인 예약 접근 차단은 test_us09_cancel.py::test_us09_other_students_reservation_forbidden
    """
    admin = make_user("admin", role=Role.ROLE_ADMIN)
    res = client.get(
        "/api/seats",
        params={"start_at": "2026-11-20T10:00:00", "end_at": "2026-11-20T12:00:00"},
        headers=auth_headers(admin),
    )
    assert res.status_code == 403 and res.json()["code"] == "FORBIDDEN_ROLE"


@pending
def test_us02_ac3_pending_account_login_blocked(client, make_user):
    """Given PENDING When 로그인 Then 403 ACCOUNT_PENDING + 이메일 인증 안내 (FR-U-03)"""
    make_user("202200003", status=AccountStatus.PENDING)
    res = _login(client, "202200003")
    assert res.status_code == 403 and res.json()["code"] == "ACCOUNT_PENDING"


@pending
def test_us02_ac4_logout_invalidates_immediately(client, make_user):
    """Given 로그인 상태 When 로그아웃 Then 같은 토큰으로 접근 불가 (FR-U-14, D-04)"""
    make_user("202200001")
    token = _login(client, "202200001").json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    assert client.get("/api/auth/me", headers=headers).status_code == 200
    assert client.post("/api/auth/logout", headers=headers).status_code == 200
    res = client.get("/api/auth/me", headers=headers)
    assert res.status_code == 401 and res.json()["code"] == "SESSION_REVOKED"


@pending
def test_us02_refresh_issues_new_access_token(client, make_user):
    """명세 4.5 Refresh 7일 (D-05): refresh 쿠키 + CSRF 헤더로 새 access token"""
    make_user("202200001")
    _login(client, "202200001")
    res = client.post("/api/auth/refresh", headers={"X-CSRF-Token": client.cookies["csrf_token"]})
    assert res.status_code == 200 and res.json()["access_token"]
