"""PolicyService — 현재 운영 정책 조회 (US-04 FR-R-03 표시용, US-05 검증용).

정책 '변경'(시험 기간 전환, US-15)은 Sprint 2.
"""

from sqlalchemy.orm import Session

from app.models import OperationPolicy
from app.repositories.policy_repository import get_current_policy
from app.schemas.seat import PolicyView


class PolicyService:
    def __init__(self, db: Session):
        self.db = db

    def current(self) -> OperationPolicy:
        return get_current_policy(self.db)

    def current_view(self) -> PolicyView:
        return PolicyView.model_validate(self.current())
