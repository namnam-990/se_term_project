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
        트랜잭션(`with transaction(self.db):`)
        User 행 FOR UPDATE → Seat 행 FOR UPDATE → 아래를 '잠금 후' 재검사
          1) request_key 이미 존재 → 기존 예약 반환 (중복 생성 X)
          2) 활성 UserRestriction → 403 USER_RESTRICTED (+ restricted_until)
          3) 정책: 과거/허용일 초과/최대시간(예약 1건 길이) 초과/운영시간·60분 단위 밖 → 400
             (D-11 운영시간·단위, D-12 1건 기준, D-13 기간 / 값은 OperationPolicy에서)
          4) 같은 학생 겹침 → 409 USER_TIME_OVERLAP
          5) 같은 좌석 겹침 → 409 SEAT_ALREADY_RESERVED
        성공 → RESERVED 저장 후 커밋. 실패 → 롤백.
        사용: user_repository.lock_by_id, seat_repository.lock_by_id, restriction_repository,
              reservation_repository(exists_overlap_*, find_by_request_key, add), PolicyService
        ※ 3) 정책 검증(FR-A-20)은 Backlog US-05 AC에 없지만 명세서 기준으로 Sprint 1에 포함 (D-25)
        """
        raise NotImplementedError("US-05 create")

    def list_mine(self, user: User, status: ReservationStatus | None):
        """US-06 (FR-R-20 필수, FR-R-21 권장): 본인 것만, 최신순, 상태 필터,
        빈 결과면 items=[] + message="예약 내역이 없습니다." (AC3)
        사용: reservation_repository.list_by_user
        """
        raise NotImplementedError("US-06 list_mine")

    def cancel_by_student(self, user: User, reservation_id: int, req: ReservationCancelRequest):
        """US-09
        - 본인 아님 → 403 NOT_OWNER (존재 노출 최소화하려면 404 — 팀 합의)
        - RESERVED 아님(CHECKED_IN·취소됨) → 409 NOT_CANCELLABLE
          (D-14: '체크인 대기' = 시작 후 15분 이내 RESERVED → 취소 허용)
        - CANCELLED, cancel_origin=STUDENT, penalty_applied=False, 사유 저장 → 좌석 즉시 가용
          (no_show_count 변경 금지 — FR-X-03)
        사용: reservation_repository.lock_by_id
        """
        raise NotImplementedError("US-09 cancel_by_student")

    def checkout(self, user: User, reservation_id: int):
        """퇴실 (Sprint 2, 설계서 4장, D-01)
        예약 잠금 → 본인·CHECKED_IN 검증 → COMPLETED + ended_at 기록 → 좌석 즉시 가용, 노쇼 없음
        """
        raise NotImplementedError("Sprint 2 checkout")

    def _now(self) -> datetime:
        return self.clock.now()
