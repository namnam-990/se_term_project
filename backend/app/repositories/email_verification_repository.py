"""EmailVerification — US-01. DB에는 코드·토큰의 해시만 저장 (security.sha256)."""

from datetime import datetime

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.models import EmailVerification


def add(db: Session, ev: EmailVerification) -> EmailVerification:
    db.add(ev)
    db.flush()
    return ev


def find_valid_by_hash(db: Session, token_hash: str, now: datetime) -> EmailVerification | None:
    """링크 토큰 또는 6자리 코드 해시로, 미사용·미만료 인증 조회 (D-03·D-15)."""
    return db.scalar(
        select(EmailVerification).where(
            EmailVerification.token_hash == token_hash,
            EmailVerification.verified_at.is_(None),
            EmailVerification.expires_at > now,
        )
    )


def invalidate_pending(db: Session, user_id: int, now: datetime) -> None:
    """재발송 시 이전 코드·링크 무효화 (D-15)."""
    db.execute(
        update(EmailVerification)
        .where(EmailVerification.user_id == user_id, EmailVerification.verified_at.is_(None))
        .values(expires_at=now)
    )
