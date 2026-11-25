"""관리자 기능 Service — US-11 강제 취소, US-12 대시보드, US-13 학생 검색,
US-16 통계, US-17 권한.

Sprint 2 스켈레톤. 담당자는 sprint2-plan.md 참고 (클래스별로 담당이 다름).
설계서 6장 추적표의 서비스 이름을 그대로 사용:
AdminReservationService · AdminDashboardService · AdminUserService · StatisticsService
모든 엔드포인트는 Router에서 require_admin으로 보호한다 (FR-U-12, D-07).
"""

from datetime import date

from sqlalchemy.orm import Session

from app.core.clock import Clock
from app.models import Reservation, Role, User
from app.schemas.admin import (
    AdminCancelRequest,
    AdminUserItem,
    AdminUserListResponse,
    DashboardResponse,
    StatisticsResponse,
)


class AdminReservationService:
    """US-11 관리자 강제 취소 (FR-X-20~22)."""

    def __init__(self, db: Session, clock: Clock):
        self.db, self.clock = db, clock

    def cancel(self, admin: User, reservation_id: int, req: AdminCancelRequest) -> Reservation:
        """US-11 AC1~3.

        - req.reason 없으면 400 REASON_REQUIRED ("취소 사유를 선택해 주세요.") — AC3
        - 사유와 패널티는 독립 선택 (D-39)
        with transaction(db):
          1. 예약을 잠금 없이 읽어 user_id 확인 → 회원 잠금 → 예약 잠금 (D-36) → 없으면 404
          2. RESERVED·CHECKED_IN만 가능, 그 외 409 NOT_CANCELLABLE (D-40)
          3. status = CANCELLED, cancel_origin = ADMIN, cancel_reason, cancel_detail,
             cancelled_by = admin.id, cancelled_at = now
             CHECKED_IN이었으면 ended_at = now (설계서 "사용 중 강제 종료 시 endedAt 기록")
          4. req.apply_penalty면 NoShowService.apply_penalty(user_id, id,
            CancelOrigin.ADMIN) — AC2, D-41
             아니면 penalty_applied = False — AC1
        좌석은 CANCELLED가 되는 순간 겹침 검사에서 빠져 즉시 가용.
        """
        raise NotImplementedError("US-11 강제 취소")


class AdminDashboardService:
    """US-12 실시간 대시보드 (FR-A-01·02)."""

    def __init__(self, db: Session, clock: Clock):
        self.db, self.clock = db, clock

    def dashboard(self) -> DashboardResponse:
        """US-12 AC1~3 / D-42 (기준 시각 = 지금, 그리드 3상태 고정).

        - 운영 좌석(enabled) 전체 + reservation_repository.list_active_at(now)
        - 좌석별: CHECKED_IN(퇴실 전) → IN_USE / RESERVED → WAITING / 나머지 → EMPTY
        - in_use, waiting, remaining = total − (in_use + waiting), utilization_rate = in_use
          / total × 100
          (total 0이면 0.0, 소수 첫째 자리 반올림)
        """
        raise NotImplementedError("US-12 대시보드")


class AdminUserService:
    """US-13 학생 목록·검색 (FR-A-10), US-17 관리자 권한 변경 (FR-A-13, Could)."""

    def __init__(self, db: Session, clock: Clock):
        self.db, self.clock = db, clock

    def list_users(
        self, student_no: str | None = None, seat_number: str | None = None
    ) -> AdminUserListResponse:
        """US-13 AC1~3.

        - 조건 없음: 전체 학생 / student_no: 학번 일치 / seat_number: 그 좌석을 지금 점유 중이거나
          오늘 남은 예약이 있는 학생 (D-43)
        - 항목: 학번·이메일·계정 상태·노쇼 횟수·restricted_until(활성 제한 종료, D-51)
          + reservations(현재·예정 예약, D-38 강제 취소 대상 찾기용)
        - 결과 없으면 items=[] + message="검색 결과가 없습니다." (AC3, 오류 아님)
        """
        raise NotImplementedError("US-13 학생 검색")

    def to_item(self, user: User) -> AdminUserItem:
        """User → AdminUserItem (restricted_until·reservations 채우기). US-13·14·17 응답 공용."""
        raise NotImplementedError("US-13 AdminUserItem 변환")

    def change_role(self, admin: User, user_id: int, role: Role) -> AdminUserItem:
        """US-17 AC1~3 (Could).

        - 본인 계정이면 400 CANNOT_CHANGE_OWN_ROLE (AC3)
        - 대상 없으면 404 USER_NOT_FOUND
        - role 변경. 권한은 요청마다 DB에서 확인하므로 즉시 반영 (D-46)
        """
        raise NotImplementedError("US-17 권한 변경")


class StatisticsService:
    """US-16 시간대별·날짜별 가동률 통계 (FR-A-03, Could)."""

    def __init__(self, db: Session, clock: Clock):
        self.db, self.clock = db, clock

    def statistics(self, from_date: date, to_date: date) -> StatisticsResponse:
        """US-16 AC1~3.

        - from > to 이면 400 INVALID_PERIOD (AC2)
        - 설계서 5장: 체크인 이력을 구간과 교차해 집계. 이용 끝 = 퇴실·강제
          종료(ended_at)·예약 종료·현재 중
          가장 이른 시각. 가동률 = 이용 좌석 분 ÷ (운영 좌석 × 운영 분) × 100
        - 이력 없으면 0% (AC3, 오류 아님)
        """
        raise NotImplementedError("US-16 통계")
