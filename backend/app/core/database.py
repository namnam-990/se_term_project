"""DB 엔진·세션 — 요청마다 Session 1개, 트랜잭션 경계는 Service가 결정한다."""

from collections.abc import Generator, Iterator
from contextlib import contextmanager

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
    """FastAPI 의존성. Service는 `with transaction(db):` 로 커밋/롤백 경계를 정한다."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def transaction(db: Session) -> Iterator[Session]:
    """Service용 트랜잭션 경계 — 성공 시 commit, 예외 시 rollback.

    ⚠️ `with db.begin():` 을 쓰지 마세요. 인증 의존성(get_current_user)이 이미 같은 세션으로
    조회를 해서 트랜잭션이 자동 시작된 상태라 "transaction already begun" 오류가 납니다.

        with transaction(self.db):
            user = user_repository.lock_by_id(self.db, user.id)
            ...
    """
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
