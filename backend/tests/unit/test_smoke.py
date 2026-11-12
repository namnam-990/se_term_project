"""스켈레톤 동작 확인 — 기능 구현과 함께 tests/unit/test_us0X_*.py 를 추가하세요."""

from app.core.security import hash_password, verify_password
from app.models import OperationPolicy


def test_health(client):
    assert client.get("/health").json() == {"status": "ok"}


def test_pages_render(client):
    for path in ["/", "/login", "/signup", "/seats", "/me/reservations"]:
        assert client.get(path).status_code == 200, path


def test_protected_api_requires_login(client):
    res = client.get(
        "/api/seats", params={"start_at": "2026-11-20T10:00:00", "end_at": "2026-11-20T12:00:00"}
    )
    assert res.status_code == 401
    assert res.json()["code"] == "AUTH_REQUIRED"


def test_bcrypt_roundtrip():
    h = hash_password("Passw0rd!")
    assert h != "Passw0rd!"
    assert verify_password("Passw0rd!", h)
    assert not verify_password("wrong", h)


def test_policy_defaults_follow_spec():
    p = OperationPolicy(
        exam_mode=False,
        normal_days_ahead=7,
        normal_max_hours=4,
        exam_days_ahead=1,
        exam_max_hours=3,
    )
    assert (p.days_ahead, p.max_hours) == (7, 4)  # 평상시 오늘~+7일, 4시간 (FR-A-20)
    p.exam_mode = True
    assert (p.days_ahead, p.max_hours) == (1, 3)  # 시험기간 당일~다음 날, 3시간


def test_clock_can_advance(clock):
    before = clock.now()
    clock.advance(minutes=15)
    assert (clock.now() - before).total_seconds() == 900
