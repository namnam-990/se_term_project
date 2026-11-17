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
            (D-03: 메일 1통에 인증 링크 + 6자리 코드 함께 / D-15: 유효 10분, 재발송 시 이전 것 무효)
        AC3 비밀번호 8자 미만/영문·숫자·특수문자 누락 → 400 PASSWORD_POLICY
        AC4 학번/이메일 중복 → 409 DUPLICATE_STUDENT_NO / DUPLICATE_EMAIL (FR-U-06)
        학교 이메일(FR-U-02): settings.allowed_email_domain 이 있으면 도메인 검사 → 400 EMAIL_DOMAIN
        사용 repository: user_repository, email_verification_repository
        """
        raise NotImplementedError("US-01 signup")

    def verify_email(self, req: EmailVerifyRequest):
        """US-01 AC2: (token) 또는 (email+code) 일치·미만료 → ACTIVE + ROLE_STUDENT (D-03)
        둘 다 없으면 400 VALIDATION_ERROR, 불일치·만료 → 400 INVALID_VERIFICATION
        """
        raise NotImplementedError("US-01 verify_email")

    def login(self, req: LoginRequest):
        """US-02 AC1·AC3, US-03 AC1~3
        - PENDING → 403 ACCOUNT_PENDING, LOCKED → 403 ACCOUNT_LOCKED (올바른 비번이어도)
        - 실패 시 failed_login_count += 1, 6번째 연속 실패 → LOCKED
        - 성공 시 failed_login_count = 0, AuthSession 생성, access/refresh 토큰 반환
        - Router는 access/refresh(HttpOnly) + csrf_token(JS 읽기 가능) 쿠키 설정 (D-02)
        - 잠금 해제 기능은 범위 밖 (D-16)
        """
        raise NotImplementedError("US-02 login")

    def refresh(self, refresh_token: str):
        """US-02 / 명세서 4.5 (D-05): refresh token(7일) 해시로 AuthSession 조회
        - 폐기·만료 → 401 SESSION_REVOKED
        - 유효 → 새 access token(1시간) 발급
        """
        raise NotImplementedError("US-02 refresh")

    def logout(self, session_id: int):
        """US-02 AC4 / FR-U-14 (D-04): AuthSession.revoked_at 기록 (쿠키 삭제는 Router)"""
        raise NotImplementedError("US-02 logout")
