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
router.add_api_route("/seats", _page("seats/grid.html"), methods=["GET"])
router.add_api_route("/me/reservations", _page("reservations/my.html"), methods=["GET"])
