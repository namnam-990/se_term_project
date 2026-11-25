"""PolicyService — 현재 운영 정책 조회 (US-04 FR-R-03 표시용, US-05 검증용) + 변경 (US-15,
Sprint 2)."""

from sqlalchemy.orm import Session

from app.models import OperationPolicy
from app.repositories.policy_repository import get_current_policy
from app.schemas.admin import PolicyUpdateRequest
from app.schemas.seat import PolicyView


class PolicyService:
    def __init__(self, db: Session):
        self.db = db

    def current(self) -> OperationPolicy:
        return get_current_policy(self.db)

    def current_view(self) -> PolicyView:
        return PolicyView.model_validate(self.current())

    # ──────────────────────────── US-15 정책 변경 (Sprint 2 스켈레톤) ────────────────────────────
    def update(self, req: PolicyUpdateRequest) -> OperationPolicy:
        """US-15 AC1·2 (FR-A-20, 명세서 4.1 "코드 변경 없이 정책 파라미터만 수정").

        with transaction(db): 정책 행(id=1)에 req 값을 그대로 저장.
        - 범위 검사는 PolicyUpdateRequest(Field ge/le)가 먼저 400으로 막음 (D-45).
          추가로 booking_rules.check_policy를 저장 전 값에 돌려 이상하면 400 INVALID_POLICY
          (Sprint 1의 503은 '이미 저장된 값이 이상할 때', D-27)
        - 운영 시간·예약 단위(open_hour·close_hour·slot_minutes)는 바꾸지 않음 (D-45, D-11)
        - 적용은 새 예약부터, 기존 예약은 그대로 (소급 없음, D-45)
        - 표시(US-04 FR-R-03)와 예약 검증(US-05, D-25)은 Sprint 1에서 이미 정책을 읽으므로 자동 반영
        """
        raise NotImplementedError("US-15 정책 변경")
