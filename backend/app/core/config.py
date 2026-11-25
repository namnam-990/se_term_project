"""환경설정 — .env 값을 읽어 타입이 있는 설정 객체로 제공한다.

예약·노쇼 정책(예약 가능 일수, 체크인 시간, 노쇼 횟수)은 OperationPolicy(DB)에 둔다.
여기는 인프라와 인증 설정(DB URL, JWT·메일, 이메일 인증 유효시간·로그인 실패 기준)을 둔다.
"""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: str = "local"
    app_debug: bool = True

    database_url: str = "mysql+pymysql://lsrs:lsrs_pw@127.0.0.1:3306/lsrs?charset=utf8mb4"

    jwt_secret_key: str = "change-me"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    refresh_token_expire_days: int = 7
    cookie_secure: bool = False
    public_base_url: str = "http://127.0.0.1:8000"
    email_verification_expire_minutes: int = Field(default=10, gt=0)  # D-15
    login_failure_limit: int = Field(default=6, gt=0)  # FR-U-13: 5회 초과

    mail_backend: str = "console"  # console | smtp
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    mail_from: str = "no-reply@lsrs.local"
    allowed_email_domain: str = ""  # 예: "university.ac.kr" (비우면 도메인 검사 생략)

    # Sprint 2 US-10 (D-37): 노쇼 감지 스케줄러. US-10 구현 전에는 False로 두고, 구현 후
    # True로 바꾼다.
    # 테스트(conftest)는 항상 끈다 — 테스트는 NoShowService.run()을 직접 호출한다.
    scheduler_enabled: bool = False

    seed_admin_login_id: str = "admin"
    seed_admin_password: str = "Admin!2345"


@lru_cache
def get_settings() -> Settings:
    return Settings()
