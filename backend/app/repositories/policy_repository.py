from sqlalchemy.orm import Session

from app.models import OperationPolicy


def read_current_policy(db: Session) -> OperationPolicy | None:
    return db.get(OperationPolicy, 1)


def get_current_policy(db: Session) -> OperationPolicy:
    """단일 정책 행. 없으면 기본값으로 생성 (seed 누락 대비)."""
    policy = read_current_policy(db)
    if policy is None:
        policy = OperationPolicy(id=1)
        db.add(policy)
        db.flush()
    return policy
