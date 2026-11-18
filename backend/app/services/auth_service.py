"""US-01·02·03 인증 업무 규칙. 쿠키 처리는 Router에 둔다."""

import re
from dataclasses import dataclass
from datetime import timedelta

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.clock import Clock
from app.core.config import get_settings
from app.core.database import transaction
from app.core.exceptions import (
    BadRequestError,
    ConflictError,
    ForbiddenError,
    ServiceUnavailableError,
    UnauthorizedError,
)
from app.core.security import (
    create_access_token,
    hash_password,
    new_numeric_code,
    new_token,
    sha256,
    verify_password,
)
from app.models import AccountStatus, AuthSession, EmailVerification, Role, User
from app.repositories import (
    auth_session_repository,
    email_verification_repository,
    user_repository,
)
from app.schemas.auth import EmailVerifyRequest, LoginRequest, LoginResponse, SignupRequest
from app.schemas.common import MessageResponse
from app.services.mail import MailSender


@dataclass
class LoginTokens:
    """Refresh 원문은 응답 본문에 노출하지 않고 Router에만 전달한다."""

    response: LoginResponse
    refresh_token: str


class AuthService:
    def __init__(self, db: Session, clock: Clock, mail: MailSender):
        self.db, self.clock, self.mail = db, clock, mail

    def _check_duplicates(self, student_no: str, email: str) -> None:
        student_exists, email_exists = user_repository.exists_student_no_or_email(
            self.db, student_no, email
        )
        if student_exists or user_repository.find_by_login_id(self.db, student_no):
            raise ConflictError("이미 등록된 학번입니다.", code="DUPLICATE_STUDENT_NO")
        if email_exists:
            raise ConflictError("이미 등록된 이메일입니다.", code="DUPLICATE_EMAIL")

    def signup(self, req: SignupRequest):
        settings = get_settings()
        password = req.password
        if not (
            len(password) >= 8
            and re.search(r"[a-zA-Z]", password)
            and re.search(r"[0-9]", password)
            and re.search(r"[^\w\s]|_", password)
            and len(password.encode("utf-8")) <= 72
        ):
            raise BadRequestError(
                "비밀번호는 8자 이상, 영문·숫자·특수문자를 포함하고 "
                "UTF-8 72바이트 이하여야 합니다.",
                code="PASSWORD_POLICY",
            )
        email = str(req.email).lower()
        domain = settings.allowed_email_domain.lower().strip().lstrip("@")
        if domain and email.rsplit("@", 1)[1] != domain:
            raise BadRequestError("학교 이메일을 입력하세요.", code="EMAIL_DOMAIN")
        try:
            with transaction(self.db):
                self._check_duplicates(req.student_no, email)
                user = user_repository.add(
                    self.db,
                    User(
                        login_id=req.student_no,
                        student_no=req.student_no,
                        email=email,
                        name=req.name,
                        password_hash=hash_password(password),
                        account_status=AccountStatus.PENDING,
                        role=Role.ROLE_STUDENT,
                    ),
                )
                token, code = new_token(), new_numeric_code()
                expires_at = self.clock.now() + timedelta(
                    minutes=settings.email_verification_expire_minutes
                )
                # D-03: 링크·코드를 각각 해시로 저장. 짧은 코드는 이메일과 결합하여
                # 서로 다른 학생에게 같은 코드가 발급되어도 UNIQUE 충돌하지 않는다.
                for digest in (sha256(token), sha256(f"{email}:{code}")):
                    email_verification_repository.add(
                        self.db,
                        EmailVerification(
                            user_id=user.id, token_hash=digest, expires_at=expires_at
                        ),
                    )
                link = f"{settings.public_base_url.rstrip('/')}/verify-email?token={token}"
                try:
                    self.mail.send(
                        email,
                        "LSRS 이메일 인증",
                        f"인증 코드: {code}\n인증 링크: {link}\n"
                        f"{settings.email_verification_expire_minutes}분 안에 인증하세요.",
                    )
                except (OSError, ValueError) as exc:
                    # 발송 실패 시 가입도 롤백하여 같은 정보로 재시도할 수 있다.
                    raise ServiceUnavailableError(
                        "인증 메일을 발송하지 못했습니다. 잠시 후 다시 가입해 주세요.",
                        code="MAIL_DELIVERY_FAILED",
                    ) from exc
        except IntegrityError:
            # 선조회 이후 동시 가입도 DB UNIQUE로 방지하고 중복 오류로 변환한다.
            self._check_duplicates(req.student_no, email)
            raise
        return {
            "user_id": user.id,
            "account_status": user.account_status,
            "message": "가입 신청이 완료되었습니다. 이메일 인증을 진행하세요.",
        }

    def verify_email(self, req: EmailVerifyRequest):
        digest = sha256(req.token) if req.token else sha256(f"{str(req.email).lower()}:{req.code}")
        with transaction(self.db):
            verification = email_verification_repository.find_valid_by_hash(
                self.db, digest, self.clock.now()
            )
            if verification is None:
                raise BadRequestError(
                    "인증 정보가 잘못되었거나 만료되었습니다.", "INVALID_VERIFICATION"
                )
            user = user_repository.lock_by_id(self.db, verification.user_id)
            now = self.clock.now()  # 잠금 대기 중 만료될 수 있으므로 다시 읽는다.
            verification = email_verification_repository.find_valid_by_hash(self.db, digest, now)
            if verification is None or user is None or user.account_status != AccountStatus.PENDING:
                raise BadRequestError(
                    "인증 정보가 잘못되었거나 만료되었습니다.", "INVALID_VERIFICATION"
                )
            verification.verified_at = now
            user.account_status = AccountStatus.ACTIVE
            user.role = Role.ROLE_STUDENT
            # 링크 또는 코드 중 하나로 성공하면 나머지도 무효화한다.
            email_verification_repository.invalidate_pending(self.db, user.id, now)
        return MessageResponse(message="이메일 인증이 완료되었습니다. 로그인해 주세요.")

    @staticmethod
    def _check_account(user: User) -> None:
        if user.account_status == AccountStatus.PENDING:
            raise ForbiddenError("이메일 인증 후 이용할 수 있습니다.", "ACCOUNT_PENDING")
        if user.account_status == AccountStatus.LOCKED:
            raise ForbiddenError("잠긴 계정입니다. 관리자에게 문의하세요.", "ACCOUNT_LOCKED")

    @staticmethod
    def _access_response(user: User, session: AuthSession) -> LoginResponse:
        return LoginResponse(
            access_token=create_access_token(user.id, user.role.value, session.id),
            role=user.role,
            expires_in=get_settings().access_token_expire_minutes * 60,
        )

    def login(self, req: LoginRequest) -> LoginTokens:
        failure = None
        result = None
        with transaction(self.db):
            user = user_repository.find_by_login_id(self.db, req.login_id)
            if user is None:
                raise UnauthorizedError("ID 또는 비밀번호가 올바르지 않습니다.", "LOGIN_FAILED")
            user = user_repository.lock_by_id(self.db, user.id)
            self._check_account(user)
            if not verify_password(req.password, user.password_hash):
                user.failed_login_count += 1
                if user.failed_login_count >= get_settings().login_failure_limit:
                    user.account_status = AccountStatus.LOCKED
                    failure = ForbiddenError(
                        "잠긴 계정입니다. 관리자에게 문의하세요.", "ACCOUNT_LOCKED"
                    )
                else:
                    failure = UnauthorizedError(
                        "ID 또는 비밀번호가 올바르지 않습니다.", "LOGIN_FAILED"
                    )
            else:
                user.failed_login_count = 0
                refresh_token = new_token()
                session = auth_session_repository.add(
                    self.db,
                    AuthSession(
                        user_id=user.id,
                        refresh_token_hash=sha256(refresh_token),
                        expires_at=self.clock.now()
                        + timedelta(days=get_settings().refresh_token_expire_days),
                    ),
                )
                result = LoginTokens(self._access_response(user, session), refresh_token)
        # 실패 횟수·LOCKED를 먼저 커밋한 뒤 오류를 반환해야 롤백되지 않는다 (US-03).
        if failure:
            raise failure
        return result

    def refresh(self, refresh_token: str) -> LoginResponse:
        with transaction(self.db):
            session = auth_session_repository.find_by_refresh_hash(self.db, sha256(refresh_token))
            if session is None:
                raise UnauthorizedError("로그아웃되었거나 만료된 세션입니다.", "SESSION_REVOKED")
            session = auth_session_repository.lock_by_id(self.db, session.id)
            if session.revoked_at is not None or session.expires_at <= self.clock.now():
                raise UnauthorizedError("로그아웃되었거나 만료된 세션입니다.", "SESSION_REVOKED")
            user = user_repository.get_by_id(self.db, session.user_id)
            if user is None:
                raise UnauthorizedError("사용자를 찾을 수 없습니다.", "TOKEN_INVALID")
            self._check_account(user)
            result = self._access_response(user, session)
        return result

    def logout(self, session_id: int):
        with transaction(self.db):
            session = auth_session_repository.lock_by_id(self.db, session_id)
            if session is None:
                raise UnauthorizedError("세션을 찾을 수 없습니다.", "SESSION_REVOKED")
            session.revoked_at = self.clock.now()
        return MessageResponse(message="로그아웃되었습니다.")
