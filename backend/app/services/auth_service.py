"""AuthService — US-01 회원가입·이메일 인증 / US-02 로그인·로그아웃 / US-03 실패 잠금.

담당: (sprint1-plan.md 참고)
"""

from sqlalchemy.orm import Session

from app.core.clock import Clock
from app.schemas.auth import EmailVerifyRequest, LoginRequest, SignupRequest
from app.services.mail import MailSender


class AuthService:
    def __init__(self, db: Session, clock: Clock, mail: MailSender):
        self.db, self.clock, self.mail = db, clock, mail

    def signup(self, req: SignupRequest):
        """US-01
        AC1 유효 입력 → PENDING 생성 + 6자리 코드 메일 발송
        AC3 비밀번호 8자 미만/영문·숫자·특수문자 누락 → 400 PASSWORD_POLICY
        AC4 학번/이메일 중복 → 409 DUPLICATE_STUDENT_NO / DUPLICATE_EMAIL
        """
        raise NotImplementedError("US-01 signup")

    def verify_email(self, req: EmailVerifyRequest):
        """US-01 AC2: 코드 일치·미만료 → ACTIVE + ROLE_STUDENT"""
        raise NotImplementedError("US-01 verify_email")

    def login(self, req: LoginRequest):
        """US-02 AC1·AC3, US-03 AC1~3
        - PENDING → 403 ACCOUNT_PENDING, LOCKED → 403 ACCOUNT_LOCKED (올바른 비번이어도)
        - 실패 시 failed_login_count += 1, 6번째 연속 실패 → LOCKED
        - 성공 시 failed_login_count = 0, AuthSession 생성, access/refresh 토큰 반환
        """
        raise NotImplementedError("US-02 login")

    def logout(self, session_id: int):
        """US-02 AC4: AuthSession.revoked_at 기록 (쿠키 삭제는 Router)"""
        raise NotImplementedError("US-02 logout")
