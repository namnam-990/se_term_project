"""RestrictionService — 이용 제한 생성·갱신·해제. US-10(자동)·US-14(수동) 공용. Sprint 2 스켈레톤.

담당: US-14 담당자가 만들고 US-10이 사용 (sprint2-plan.md 공유 부품)
명세서: FR-R-12, FR-X-12, FR-A-11, FR-A-21 / 설계서:
  UserRestriction(startsAt·endsAt·releasedAt·source)

D-51 이용 제한 상태 정의
- 계정 상태(PENDING·ACTIVE·LOCKED)와 별개. UserRestriction 행으로 판단.
- 활성 = starts_at ≤ 지금 < ends_at 이고 released_at IS NULL (restriction_repository.find_active).
- 막는 것: **새 예약 생성만** (Sprint 1 ReservationService.create에서 이미 검사, 403
  USER_RESTRICTED).
  로그인·조회·취소·기존 예약 체크인·퇴실은 막지 않는다. 기존 예약은 유지(D-44).
- 자동 해제: 별도 작업 없이 ends_at이 지나면 비활성. 이력은 삭제하지 않는다.
"""

from datetime import date, datetime

from sqlalchemy.orm import Session

from app.core.clock import Clock
from app.models import User, UserRestriction


class RestrictionService:
    def __init__(self, db: Session, clock: Clock):
        self.db, self.clock = db, clock

    def apply_no_show_restriction(self, user: User, now: datetime, days: int) -> UserRestriction:
        """US-10 AC2 / D-17(개정): 노쇼 기준 이상일 때 호출 (회원 행은 호출자가 이미 잠금).

        - 활성 제한이 없으면: UserRestriction(source=AUTO_NO_SHOW, starts_at=now,
          ends_at=now+days) 추가
        - 이미 활성 제한이 있으면: 종료일 = max(기존 ends_at, now+days) — 관리자가 더 길게
          건 제한은 줄이지 않음
        """
        raise NotImplementedError("US-10 자동 제한")

    def set_manual(self, admin: User, user_id: int, until: date, reason: str | None) -> User:
        """US-14 AC1 (FR-A-11·21): 관리자 수동 제한.

        - ends_at = until 다음 날 00:00 (그 날짜가 끝날 때까지 차단, D-51)
        - until이 오늘보다 이전이면 400 INVALID_RESTRICTION_DATE
        - 이미 활성 제한이 있으면 종료일을 새 값으로 갱신 (설계서 "제한 설정·기간 갱신")
        - 없으면 UserRestriction(source=ADMIN, starts_at=now, ends_at=…, reason) 추가
        - 대상이 없거나 학생이 아니면 404 USER_NOT_FOUND
        """
        raise NotImplementedError("US-14 수동 제한 설정")

    def release(self, admin: User, user_id: int) -> User:
        """US-14 AC2 (FR-A-11·21): 활성 제한 전부에 released_at = now → 즉시 예약 가능.

        노쇼 카운터는 건드리지 않는다 (초기화는 NoShowService.reset, D-17).
        활성 제한이 없어도 오류 없이 그대로 반환.
        """
        raise NotImplementedError("US-14 제한 해제")
