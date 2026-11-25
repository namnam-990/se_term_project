"""스켈레톤 동작 확인 — 기능 구현과 함께 tests/unit/test_us0X_*.py 를 추가하세요."""

from app.core.security import hash_password, verify_password
from app.models import OperationPolicy


def test_health(client):
    assert client.get("/health").json() == {"status": "ok"}


def test_pages_render(client):
    for path in ["/", "/login", "/signup", "/seats", "/me/reservations"]:
        assert client.get(path).status_code == 200, path


def test_sprint2_pages_render(client):
    """Sprint 2 화면 틀 (스켈레톤) — 데이터는 각 화면 JS가 API로 불러온다."""
    for path in ["/kiosk", "/admin", "/admin/users", "/admin/policy", "/admin/statistics"]:
        assert client.get(path).status_code == 200, path


def test_sprint2_apis_require_login(client):
    """Sprint 2 API가 등록돼 있고(404 아님), 로그인 없이는 서비스(501)까지 가지 않는다.

    GET은 401 AUTH_REQUIRED, POST·PUT·DELETE는 CSRF 검사가 먼저라 403 CSRF_FAILED.
    """
    calls = [
        ("get", "/api/reservations/1/qr"),
        ("post", "/api/reservations/1/check-in"),
        ("post", "/api/reservations/1/checkout"),
        ("post", "/api/admin/reservations/1/cancel"),
        ("get", "/api/admin/dashboard"),
        ("get", "/api/admin/users"),
        ("put", "/api/admin/users/1/restriction"),
        ("delete", "/api/admin/users/1/restriction"),
        ("post", "/api/admin/users/1/no-shows/reset"),
        ("put", "/api/admin/policies/current"),
        ("get", "/api/admin/statistics?from=2026-11-20&to=2026-11-20"),
        ("put", "/api/admin/users/1/role"),
    ]
    for method, path in calls:
        expected = 401 if method == "get" else 403
        assert getattr(client, method)(path).status_code == expected, (method, path)


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
