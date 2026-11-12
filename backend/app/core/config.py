"""환경설정 — .env 값을 읽어 타입이 있는 설정 객체로 제공한다.

업무 정책(예약 가능 일수, 15분, 3회 등)은 여기 두지 않는다. → OperationPolicy(DB)
여기는 인프라 설정(DB URL, JWT 비밀키, 메일 서버)만 둔다.
"""

from functools import lru_cache

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

    mail_backend: str = "console"  # console | smtp
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    mail_from: str = "no-reply@lsrs.local"
    allowed_email_domain: str = ""  # 예: "university.ac.kr" (비우면 도메인 검사 생략)

    seed_admin_login_id: str = "admin"
    seed_admin_password: str = "Admin!2345"


@lru_cache
def get_settings() -> Settings:
    return Settings()
