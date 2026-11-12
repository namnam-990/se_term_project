"""DB 엔진·세션 — 요청마다 Session 1개, 트랜잭션 경계는 Service가 결정한다."""

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import get_settings


class Base(DeclarativeBase):
    pass


def _make_engine(url: str):
    kwargs: dict = {"pool_pre_ping": True}
    if url.startswith("mysql"):
        # FOR UPDATE 잠금 후 재조회 시 최신 커밋 데이터를 보도록 READ COMMITTED 사용
        kwargs["isolation_level"] = "READ COMMITTED"
    return create_engine(url, **kwargs)


engine = _make_engine(get_settings().database_url)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db() -> Generator[Session, None, None]:
    """FastAPI 의존성. Service 안에서 `with db.begin():` 으로 트랜잭션을 연다."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
