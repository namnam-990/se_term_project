"""SeatQueryService — US-04 날짜·시간대별 좌석 4상태 조회.

담당: (sprint1-plan.md 참고)
"""

from datetime import datetime

from sqlalchemy.orm import Session

from app.core.clock import Clock
from app.models import User


class SeatQueryService:
    def __init__(self, db: Session, clock: Clock):
        self.db, self.clock = db, clock

    def get_grid(self, user: User, start_at: datetime, end_at: datetime):
        """US-04
        AC1 전체 좌석 + 4상태(AVAILABLE/IN_USE/MINE/RESERVED), 500ms 이내 → 쿼리 2~3회로 끝낼 것
        AC2 시간대 변경 시 재계산 (상태는 저장값이 아닌 계산값)
        AC3 과거 시간 / 정책 예약 가능 일수 초과 → 400 OUT_OF_BOOKING_WINDOW
        AC4 (FR-R-03, D-06·D-22) 응답에 현재 정책(시험 기간 여부·최대 시간·예약 가능 기간) 포함
        기간 판단 기준 = 시작 시각의 날짜, 평상시 오늘~+7일 / 시험 기간 오늘~내일 (D-13)
        상태 계산: 요청 구간과 겹치는 RESERVED·CHECKED_IN 예약 기준
          내 예약 → MINE / 타인 CHECKED_IN → IN_USE / 타인 RESERVED → RESERVED / 없음 → AVAILABLE
        사용: seat_repository.list_enabled, reservation_repository.find_overlapping, PolicyService
        """
        raise NotImplementedError("US-04 get_grid")
