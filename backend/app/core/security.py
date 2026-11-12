"""보안 유틸 — BCrypt 해시(요구사항 4.5), JWT 발급/검증, 토큰 해시.

여기는 '도구'만 둔다. 로그인 실패 횟수·잠금·세션 저장 같은 업무 규칙은
AuthService(US-02/03)에서 구현.
"""

import hashlib
import secrets
from datetime import datetime, timedelta

import bcrypt
import jwt

from app.core.config import get_settings


# ── 비밀번호 ────────────────────────────────────────────
def hash_password(raw: str) -> str:
    return bcrypt.hashpw(raw.encode(), bcrypt.gensalt()).decode()


def verify_password(raw: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(raw.encode(), hashed.encode())
    except ValueError:
        return False


# ── 임의 토큰 / 해시 (이메일 인증 코드, refresh token 등 DB에는 해시만 저장) ──
def new_token(nbytes: int = 32) -> str:
    return secrets.token_urlsafe(nbytes)


def new_numeric_code(digits: int = 6) -> str:
    return "".join(secrets.choice("0123456789") for _ in range(digits))


def sha256(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


# ── JWT ────────────────────────────────────────────────
def create_access_token(user_id: int, role: str, session_id: int, now: datetime) -> str:
    s = get_settings()
    payload = {
        "sub": str(user_id),
        "role": role,
        "sid": session_id,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=s.access_token_expire_minutes)).timestamp()),
        "typ": "access",
    }
    return jwt.encode(payload, s.jwt_secret_key, algorithm=s.jwt_algorithm)


def decode_access_token(token: str) -> dict:
    """만료·서명 오류 시 jwt.PyJWTError 발생 → 호출 측에서 401 처리."""
    s = get_settings()
    payload = jwt.decode(token, s.jwt_secret_key, algorithms=[s.jwt_algorithm])
    if payload.get("typ") != "access":
        raise jwt.InvalidTokenError("not an access token")
    return payload
