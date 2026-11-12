"""ReservationService — US-05 예약 생성(동시성 제어) / US-06 내역 조회 / US-09 직접 취소.

담당: (sprint1-plan.md 참고)
설계서 Core Flow 1 참고.
"""

from datetime import datetime

from sqlalchemy.orm import Session

from app.core.clock import Clock
from app.models import ReservationStatus, User
from app.schemas.reservation import ReservationCancelRequest, ReservationCreateRequest


class ReservationService:
    def __init__(self, db: Session, clock: Clock):
        self.db, self.clock = db, clock

    def create(self, user: User, req: ReservationCreateRequest):
        """US-05 (Core Flow 1)
        트랜잭션: User 행 FOR UPDATE → Seat 행 FOR UPDATE → 아래를 '잠금 후' 재검사
          1) request_key 이미 존재 → 기존 예약 반환 (중복 생성 X)
          2) 활성 UserRestriction → 403 USER_RESTRICTED (+ restricted_until)
          3) 정책: 과거/허용일 초과/최대시간 초과/운영시간 밖 → 400
          4) 같은 학생 겹침 → 409 USER_TIME_OVERLAP
          5) 같은 좌석 겹침 → 409 SEAT_ALREADY_RESERVED
        성공 → RESERVED 저장 후 커밋. 실패 → 롤백.
        """
        raise NotImplementedError("US-05 create")

    def list_mine(self, user: User, status: ReservationStatus | None):
        """US-06: 본인 것만, created_at/start_at 최신순, 상태 필터, 빈 결과 안내"""
        raise NotImplementedError("US-06 list_mine")

    def cancel_by_student(self, user: User, reservation_id: int, req: ReservationCancelRequest):
        """US-09
        - 본인 아님 → 403 NOT_OWNER (존재 노출 최소화하려면 404 — 팀 합의)
        - RESERVED 아님 → 409 NOT_CANCELLABLE
        - CANCELLED, cancel_origin=STUDENT, penalty_applied=False, 사유 저장 → 좌석 즉시 가용
        """
        raise NotImplementedError("US-09 cancel_by_student")

    def _now(self) -> datetime:
        return self.clock.now()
