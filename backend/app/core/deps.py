"""공통 FastAPI 의존성 — 인증/권한 (US-02).

⚠️ 팀 공용 계약: 모든 Router가 `current_user = Depends(get_current_user)` 또는
`Depends(require_student)` / `Depends(require_admin)` 으로 사용한다.
시그니처를 바꿀 때는 PR에 반드시 팀 전체를 리뷰어로 지정할 것.

토큰 위치: HttpOnly 쿠키 `access_token` (화면) 또는 `Authorization: Bearer` (Swagger·테스트)
"""

import jwt
from fastapi import Depends, Request
from sqlalchemy.orm import Session

from app.core.clock import Clock, get_clock
from app.core.database import get_db
from app.core.exceptions import ForbiddenError, UnauthorizedError
from app.core.security import decode_access_token
from app.models import AccountStatus, AuthSession, Role, User

ACCESS_COOKIE = "access_token"
REFRESH_COOKIE = "refresh_token"


def _extract_token(request: Request) -> str | None:
    auth = request.headers.get("Authorization", "")
    if auth.lower().startswith("bearer "):
        return auth[7:]
    return request.cookies.get(ACCESS_COOKIE)


def get_current_user(
    request: Request,
    db: Session = Depends(get_db),
    clock: Clock = Depends(get_clock),
) -> User:
    token = _extract_token(request)
    if not token:
        raise UnauthorizedError("로그인이 필요합니다.", code="AUTH_REQUIRED")
    try:
        payload = decode_access_token(token)
    except jwt.PyJWTError as e:
        raise UnauthorizedError(
            "인증이 만료되었거나 올바르지 않습니다.", code="TOKEN_INVALID"
        ) from e

    # 설계서: 요청마다 세션 폐기 여부·현재 DB 권한을 확인 (로그아웃 즉시 무효화)
    sid = payload.get("sid")
    session = db.get(AuthSession, sid) if sid is not None else None
    if session is None or session.revoked_at is not None or session.expires_at <= clock.now():
        raise UnauthorizedError("로그아웃되었거나 만료된 세션입니다.", code="SESSION_REVOKED")

    user = db.get(User, int(payload["sub"]))
    if user is None:
        raise UnauthorizedError("사용자를 찾을 수 없습니다.", code="TOKEN_INVALID")
    if user.account_status == AccountStatus.PENDING:
        raise ForbiddenError("이메일 인증 후 이용할 수 있습니다.", code="ACCOUNT_PENDING")
    if user.account_status == AccountStatus.LOCKED:
        raise ForbiddenError("잠긴 계정입니다. 관리자에게 문의하세요.", code="ACCOUNT_LOCKED")
    return user


def require_student(user: User = Depends(get_current_user)) -> User:
    if user.role != Role.ROLE_STUDENT:
        raise ForbiddenError("학생만 이용할 수 있는 기능입니다.", code="FORBIDDEN_ROLE")
    return user


def require_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != Role.ROLE_ADMIN:
        raise ForbiddenError("관리자 권한이 필요합니다.", code="FORBIDDEN_ROLE")
    return user
