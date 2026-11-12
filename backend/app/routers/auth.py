"""Auth Router — HTTP 입출력만. 업무 규칙은 AuthService.  (US-01·02·03)"""

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.core.clock import Clock, get_clock
from app.core.database import get_db
from app.core.deps import get_current_user
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
    # TODO(US-02): svc.login() 결과로 HttpOnly 쿠키(access_token, refresh_token) 설정
    return svc.login(req)


@router.post("/logout", response_model=MessageResponse)
def logout(
    response: Response,
    user: User = Depends(get_current_user),
    svc: AuthService = Depends(get_auth_service),
):
    # TODO(US-02): 토큰의 sid로 세션 폐기 + 쿠키 삭제
    raise NotImplementedError("US-02 logout")


@router.get("/me", response_model=MeResponse)
def me(user: User = Depends(get_current_user)):
    return user
