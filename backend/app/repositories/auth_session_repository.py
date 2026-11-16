"""AuthSession — US-02 로그인·refresh·로그아웃 (D-04·D-05)."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import AuthSession


def add(db: Session, session: AuthSession) -> AuthSession:
    db.add(session)
    db.flush()
    return session


def find_by_refresh_hash(db: Session, refresh_token_hash: str) -> AuthSession | None:
    return db.scalar(
        select(AuthSession).where(AuthSession.refresh_token_hash == refresh_token_hash)
    )
