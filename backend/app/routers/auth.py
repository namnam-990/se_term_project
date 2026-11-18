"""Auth Router — HTTP 입출력만. 업무 규칙은 AuthService.  (US-01·02·03)"""

from fastapi import APIRouter, Depends, Request, Response, status
from sqlalchemy.orm import Session

from app.core.clock import Clock, get_clock
from app.core.config import get_settings
from app.core.csrf import CSRF_COOKIE, new_csrf_token, verify_csrf
from app.core.database import get_db
from app.core.deps import ACCESS_COOKIE, REFRESH_COOKIE, get_current_user
from app.core.exceptions import UnauthorizedError
from app.models import User
from app.schemas.auth import (
    EmailVerifyRequest,
    LoginRequest,
    LoginResponse,
    MeResponse,
    SignupRequest,
    SignupResponse,
)
from app.schemas.common import MessageResponse
from app.services.auth_service import AuthService
from app.services.mail import MailSender, get_mail_sender

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _set_access_cookies(
    response: Response, access_token: str, csrf_token: str | None = None
) -> None:
    settings = get_settings()
    options = {"secure": settings.cookie_secure, "samesite": "lax", "path": "/"}
    response.set_cookie(
        ACCESS_COOKIE,
        access_token,
        httponly=True,
        max_age=settings.access_token_expire_minutes * 60,
        **options,
    )
    # Access 만료 후에도 Refresh 요청을 검증할 수 있도록 CSRF 쿠키는 7일 유지.
    response.set_cookie(
        CSRF_COOKIE,
        csrf_token or new_csrf_token(),
        httponly=False,
        max_age=settings.refresh_token_expire_days * 86400,
        **options,
    )


def get_auth_service(
    db: Session = Depends(get_db),
    clock: Clock = Depends(get_clock),
    mail: MailSender = Depends(get_mail_sender),
) -> AuthService:
    return AuthService(db, clock, mail)


@router.post("/signup", response_model=SignupResponse, status_code=status.HTTP_201_CREATED)
def signup(req: SignupRequest, svc: AuthService = Depends(get_auth_service)):
    return svc.signup(req)


@router.post("/email-verifications", response_model=MessageResponse)
def verify_email(req: EmailVerifyRequest, svc: AuthService = Depends(get_auth_service)):
    return svc.verify_email(req)


@router.post("/login", response_model=LoginResponse)
def login(req: LoginRequest, response: Response, svc: AuthService = Depends(get_auth_service)):
    tokens = svc.login(req)
    _set_access_cookies(response, tokens.response.access_token)
    settings = get_settings()
    response.set_cookie(
        REFRESH_COOKIE,
        tokens.refresh_token,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        path="/",
        max_age=settings.refresh_token_expire_days * 86400,
    )
    return tokens.response


@router.post("/refresh", response_model=LoginResponse, dependencies=[Depends(verify_csrf)])
def refresh(request: Request, response: Response, svc: AuthService = Depends(get_auth_service)):
    token = request.cookies.get(REFRESH_COOKIE)
    if not token:
        raise UnauthorizedError("다시 로그인해 주세요.", "AUTH_REQUIRED")
    result = svc.refresh(token)
    # 다른 탭·동시 요청의 헤더를 무효화하지 않도록 기존 CSRF 값을 유지한다.
    _set_access_cookies(response, result.access_token, request.cookies.get(CSRF_COOKIE))
    return result


@router.post("/logout", response_model=MessageResponse, dependencies=[Depends(verify_csrf)])
def logout(
    request: Request,
    response: Response,
    user: User = Depends(get_current_user),
    svc: AuthService = Depends(get_auth_service),
):
    result = svc.logout(request.state.auth_session_id)
    for cookie in (ACCESS_COOKIE, REFRESH_COOKIE, CSRF_COOKIE):
        response.delete_cookie(
            cookie,
            path="/",
            secure=get_settings().cookie_secure,
            httponly=cookie != CSRF_COOKIE,
            samesite="lax",
        )
    return result


@router.get("/me", response_model=MeResponse)
def me(user: User = Depends(get_current_user)):
    return user
