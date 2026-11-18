"""US-04 날짜·시간대별 좌석 현황 조회."""

from datetime import datetime

from sqlalchemy.orm import Session

from app.core.clock import Clock
from app.core.exceptions import ServiceUnavailableError
from app.models import ReservationStatus, User
from app.models.enums import SeatViewStatus
from app.repositories.policy_repository import read_current_policy
from app.repositories.reservation_repository import find_overlapping
from app.repositories.seat_repository import list_enabled
from app.schemas.seat import PolicyView, SeatGridResponse, SeatView
from app.services.booking_rules import validate_view

STATUS_PRIORITY = {
    SeatViewStatus.AVAILABLE: 0,
    SeatViewStatus.RESERVED: 1,
    SeatViewStatus.IN_USE: 2,
    SeatViewStatus.MINE: 3,
}


class SeatQueryService:
    def __init__(self, db: Session, clock: Clock):
        self.db, self.clock = db, clock

    def get_grid(self, user: User, start_at: datetime, end_at: datetime) -> SeatGridResponse:
        policy = read_current_policy(self.db)
        if policy is None:
            raise ServiceUnavailableError(
                "운영 정책이 등록되지 않았습니다. 관리자에게 문의하세요.",
                "OPERATION_POLICY_UNAVAILABLE",
            )
        # 시간 규칙은 예약(US-05)과 같은 booking_rules 사용 — 조회는 진행 중 시간대까지 허용
        validate_view(start_at, end_at, self.clock.now(), policy)

        seats: dict[int, SeatView] = {}
        for seat in list_enabled(self.db):
            seats[seat.id] = SeatView(
                seat_id=seat.id,
                seat_number=seat.seat_number,
                grid_row=seat.grid_row,
                grid_col=seat.grid_col,
                status=SeatViewStatus.AVAILABLE,
            )

        for reservation in find_overlapping(self.db, start_at, end_at):
            view = seats.get(reservation.seat_id)
            if view is None:
                continue
            if reservation.user_id == user.id:
                status = SeatViewStatus.MINE
            elif reservation.status == ReservationStatus.CHECKED_IN:
                status = SeatViewStatus.IN_USE
            else:
                status = SeatViewStatus.RESERVED
            if STATUS_PRIORITY[status] > STATUS_PRIORITY[view.status]:
                view.status = status

        return SeatGridResponse(
            date=start_at.date(),
            start_at=start_at,
            end_at=end_at,
            policy=PolicyView.model_validate(policy),
            seats=list(seats.values()),
        )
