"""CSRF 방어 — 설계서 5장 "상태 변경 CSRF 검증" (D-02).

방식: Double Submit Cookie
- 로그인 성공 시 Router가 `csrf_token` 쿠키(HttpOnly 아님, JS가 읽을 수 있음)를 함께 설정
- 화면 JS(static/js/api.js)는 POST/PUT/DELETE 때 쿠키 값을 `X-CSRF-Token` 헤더로 보냄
- 서버는 쿠키 값과 헤더 값이 같은지만 확인
- `Authorization: Bearer` 로 호출하는 경우(Swagger·테스트)는 쿠키 인증이 아니므로 검사 생략
"""

import secrets

from fastapi import Request

from app.core.exceptions import ForbiddenError

CSRF_COOKIE = "csrf_token"
CSRF_HEADER = "X-CSRF-Token"


def new_csrf_token() -> str:
    return secrets.token_urlsafe(32)


def verify_csrf(request: Request) -> None:
    if request.headers.get("Authorization", "").lower().startswith("bearer "):
        return
    cookie = request.cookies.get(CSRF_COOKIE)
    header = request.headers.get(CSRF_HEADER)
    if not cookie or not header or not secrets.compare_digest(cookie, header):
        raise ForbiddenError("요청 검증에 실패했습니다. 다시 로그인해 주세요.", code="CSRF_FAILED")
