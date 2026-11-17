"""US-03 로그인 실패 횟수 초과 시 계정 잠금 — FR-U-13 (Should / 3 SP, 명세서 '권장')"""

import pytest

from app.models import AccountStatus, User
from tests.conftest import DEFAULT_PASSWORD

pending = pytest.mark.skip(reason="US-03 구현 전 — 구현 후 이 데코레이터를 지우세요")


def _login(client, password):
    return client.post("/api/auth/login", json={"login_id": "202200001", "password": password})


@pending
def test_us03_ac1_sixth_failure_locks(client, db_session, make_user):
    """Given 연속 실패 5회 When 6번째도 실패 Then LOCKED + 안내 ('5회 초과' = 6번째)"""
    make_user("202200001")
    for _ in range(5):
        assert _login(client, "Wrong!234").status_code == 401  # 1~5번째: 아직 잠기지 않음
    res = _login(client, "Wrong!234")
    assert res.status_code == 403 and res.json()["code"] == "ACCOUNT_LOCKED"
    user = db_session.query(User).filter_by(login_id="202200001").one()
    db_session.refresh(user)
    assert user.account_status == AccountStatus.LOCKED


@pending
def test_us03_ac2_locked_rejects_correct_password(client, make_user):
    """Given LOCKED When 올바른 비밀번호 Then 거부 (시간 제한 없음, 해제는 범위 밖 D-16)"""
    make_user("202200001", status=AccountStatus.LOCKED)
    res = _login(client, DEFAULT_PASSWORD)
    assert res.status_code == 403 and res.json()["code"] == "ACCOUNT_LOCKED"


@pending
def test_us03_ac3_success_resets_fail_count(client, db_session, make_user):
    """Given 실패 3회 When 성공 Then 실패 횟수 0 → 이후 5번 더 틀려도 잠기지 않음"""
    make_user("202200001")
    for _ in range(3):
        _login(client, "Wrong!234")
    assert _login(client, DEFAULT_PASSWORD).status_code == 200
    user = db_session.query(User).filter_by(login_id="202200001").one()
    db_session.refresh(user)
    assert user.failed_login_count == 0
