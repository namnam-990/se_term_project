"""화면(Jinja2) 라우트 — 화면은 정적 틀만 렌더링하고, 데이터는 JS fetch로 /api/* 호출."""

from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates

router = APIRouter(include_in_schema=False)
templates = Jinja2Templates(directory="app/templates")


def _page(name: str):
    def handler(request: Request):
        return templates.TemplateResponse(request, name)

    return handler


router.add_api_route("/", _page("index.html"), methods=["GET"])
router.add_api_route("/signup", _page("auth/signup.html"), methods=["GET"])
router.add_api_route("/login", _page("auth/login.html"), methods=["GET"])
router.add_api_route("/verify-email", _page("auth/verify.html"), methods=["GET"])
router.add_api_route("/seats", _page("seats/grid.html"), methods=["GET"])
router.add_api_route("/me/reservations", _page("reservations/my.html"), methods=["GET"])

# Sprint 2 화면 (스켈레톤) — 데이터는 각 화면 JS가 /api/* 로 불러온다. 권한 검사는 API가 한다.
router.add_api_route("/kiosk", _page("checkin/kiosk.html"), methods=["GET"])  # US-08 체크인 단말
router.add_api_route("/admin", _page("admin/dashboard.html"), methods=["GET"])  # US-12
router.add_api_route("/admin/users", _page("admin/users.html"), methods=["GET"])  # US-11·13·14·17
router.add_api_route("/admin/policy", _page("admin/policy.html"), methods=["GET"])  # US-15
router.add_api_route("/admin/statistics", _page("admin/statistics.html"), methods=["GET"])  # US-16
