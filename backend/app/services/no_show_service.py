"""NoShowService — US-10 노쇼 자동 취소·카운터·자동 제한, US-11 패널티, US-14 초기화. Sprint
2 스켈레톤.

담당: US-10 담당자 (run·apply) / US-14 담당자 (reset) — sprint2-plan.md
명세서: FR-C-04, FR-X-10~13, FR-X-22, FR-A-12 / 설계서 Core Flow 3

결정
- D-37: 업무 로직은 전부 여기. 스케줄러(core/scheduler.py)는 run()을 호출만 한다.
        테스트는 FixedClock으로 run()을 직접 호출 (명세서 4.2 시간 조작).
- D-34: 마감(시작+15분) 후 run()이 처리할 때까지 좌석 점유 유지. 처리 순간 AUTO_CANCELLED →
  즉시 가용(FR-X-13).
- D-36: 잠금 순서 회원 → 예약. 건마다 트랜잭션 1개 (한 건 실패해도 나머지는 처리, 실패 건은
  다음 실행에서 재검사).
- D-17(개정): 카운터 +1 후 카운터 ≥ no_show_threshold면 RestrictionService로 restriction_days 제한.
        3회째부터 노쇼마다 다시 제한, 이미 제한 중이면 종료일 = max(기존, 지금+일수).
        자동 해제는 제한만 끝냄 — **카운터는 그대로**. 0으로 만드는 건 reset()뿐. 카운터는
          3에서 멈추지 않음(FR-X-11).
- D-41: 관리자 강제 취소의 패널티도 apply()를 같이 쓴다 (source=ADMIN).
- 제한 시작·노쇼 발생 시각 = 처리 시각(now) (Backlog US-10 AC2 "노쇼 처리가 완료되면 즉시").
"""

from sqlalchemy.orm import Session

from app.core.clock import Clock
from app.models import CancelOrigin, User


class NoShowService:
    def __init__(self, db: Session, clock: Clock):
        self.db, self.clock = db, clock

    def run(self) -> int:
        """US-10 AC1: 스케줄러가 10분마다 호출. 처리한 건수 반환.

        now = clock.now()
        ids = reservation_repository.find_no_show_candidates(db, now, policy.check_in_minutes)
        for id in ids: 건마다 try: self._auto_cancel(id) except: 로그 남기고 다음 건
        """
        raise NotImplementedError("US-10 노쇼 감지 run()")

    def _auto_cancel(self, reservation_id: int) -> bool:
        """US-10 AC1~2: 후보 1건 처리. 처리했으면 True, 이미 처리됐거나 조건이 바뀌었으면 False.

        with transaction(db):
          1. 예약을 잠금 없이 읽어 user_id 확인 → user_repository.lock_by_id (회원 먼저, D-36)
          2. reservation_repository.lock_by_id → **다시 확인**: 아직 RESERVED이고 마감이 지났는가
             (그 사이 체크인·취소됐으면 False — 체크인과 경합 시 하나만 확정, 설계서 Core Flow 3)
          3. status = AUTO_CANCELLED, cancel_origin = SYSTEM, cancelled_at = now
          4. self.apply_penalty(user_id, reservation_id, CancelOrigin.SYSTEM)
        """
        raise NotImplementedError("US-10 노쇼 자동 취소 _auto_cancel()")

    def apply_penalty(self, user_id: int, reservation_id: int, source: CancelOrigin) -> None:
        """노쇼 1건 반영 — US-10(source=SYSTEM)·US-11(source=ADMIN, 패널티 선택 시) 공용.

        **호출하는 쪽의 트랜잭션 안에서, 회원 행을 이미 잠근 상태로** 부른다 (D-36).
          1. NoShowEvent(user_id, reservation_id, source, occurred_at=now) 추가 (UNIQUE →
            이중 집계 방지)
          2. user.no_show_count += 1
          3. no_show_count ≥ policy.no_show_threshold 이면
             RestrictionService.apply_no_show_restriction(user, now, policy.restriction_days)
          4. reservation.penalty_applied = True
        """
        raise NotImplementedError("US-10 노쇼 반영 apply_penalty()")

    def reset(self, admin: User, user_id: int) -> User:
        """US-14 AC3 (FR-A-12): 노쇼 카운터 0 + 이력 보존 (설계서 "노쇼 누적 초기화·이력 보존").

        with transaction(db):
          1. user_repository.lock_by_id → 없거나 학생이 아니면 404 USER_NOT_FOUND
          2. user.no_show_count = 0
          3. no_show_event_repository.mark_reset(db, user_id, now)  # 행은 지우지 않음
        진행 중인 이용 제한은 풀지 않는다 (해제는 RestrictionService.release, D-51).
        카운터가 이미 0이어도 오류 없이 그대로 반환.
        """
        raise NotImplementedError("US-14 노쇼 초기화 reset()")
