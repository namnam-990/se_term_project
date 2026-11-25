"""NoShowEvent 저장·초기화 — US-10·11·14 (Sprint 2, 스켈레톤).

설계서: NoShowEvent.reservation_id UNIQUE → 같은 예약이 두 번 집계되지 않음 (이중 노쇼 방지).
초기화(FR-A-12)는 행을 지우지 않고 reset_at만 기록 → "노쇼 누적 초기화·이력 보존".
"""

from datetime import datetime

from sqlalchemy.orm import Session

from app.models import NoShowEvent


def add(db: Session, event: NoShowEvent) -> NoShowEvent:
    """US-10·11: 노쇼 1건 기록. UNIQUE 위반이면 이미 처리된 예약 → Service가 건너뛴다."""
    raise NotImplementedError("US-10 no_show_event_repository.add")


def mark_reset(db: Session, user_id: int, now: datetime) -> int:
    """US-14 AC3: 그 학생의 아직 초기화 안 된 노쇼(reset_at IS NULL)에 reset_at = now. 바뀐
    행 수 반환."""
    raise NotImplementedError("US-14 no_show_event_repository.mark_reset")
