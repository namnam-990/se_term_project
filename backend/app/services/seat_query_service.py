"""US-04 날짜·시간대별 좌석 현황 조회."""

from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.core.clock import Clock
from app.core.exceptions import BadRequestError, ServiceUnavailableError
from app.models import OperationPolicy, ReservationStatus, User
from app.models.enums import SeatViewStatus
from app.repositories.policy_repository import read_current_policy
from app.repositories.seat_repository import list_seats_with_overlaps
from app.schemas.seat import PolicyView, SeatGridResponse, SeatView

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
        self._validate_range(start_at, end_at, policy)

        seats: dict[int, SeatView] = {}
        for seat, reservation in list_seats_with_overlaps(self.db, start_at, end_at):
            view = seats.get(seat.id)
            if view is None:
                view = SeatView(
                    seat_id=seat.id,
                    seat_number=seat.seat_number,
                    grid_row=seat.grid_row,
                    grid_col=seat.grid_col,
                    status=SeatViewStatus.AVAILABLE,
                )
                seats[seat.id] = view

            if reservation is None:
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

    def _validate_range(
        self, start_at: datetime, end_at: datetime, policy: OperationPolicy
    ) -> None:
        if start_at.tzinfo is not None or end_at.tzinfo is not None or start_at >= end_at:
            raise BadRequestError(
                "한국 시간 기준으로 시작·종료 시간을 올바르게 입력하세요.", "INVALID_TIME_RANGE"
            )

        if not (
            0 <= policy.open_hour < policy.close_hour <= 24
            and 0 < policy.slot_minutes <= (policy.close_hour - policy.open_hour) * 60
            and policy.days_ahead >= 0
        ):
            raise ServiceUnavailableError(
                "운영 정책의 시간 설정이 올바르지 않습니다. 관리자에게 문의하세요.",
                "OPERATION_POLICY_UNAVAILABLE",
            )

        now = self.clock.now()
        days_from_today = (start_at.date() - now.date()).days
        if end_at <= now or days_from_today > policy.days_ahead:
            raise BadRequestError(
                "이미 끝난 시간대나 예약 가능 기간을 벗어난 시간은 조회할 수 없습니다.",
                "OUT_OF_BOOKING_WINDOW",
            )

        day_start = start_at.replace(hour=0, minute=0, second=0, microsecond=0)
        opens = timedelta(hours=policy.open_hour)
        closes = timedelta(hours=policy.close_hour)
        start_offset = start_at - day_start
        end_offset = end_at - day_start
        slot = timedelta(minutes=policy.slot_minutes)
        if (
            start_offset < opens
            or end_offset > closes
            or (start_offset - opens) % slot
            or (end_offset - opens) % slot
        ):
            raise BadRequestError(
                f"운영 시간({policy.open_hour:02d}:00~{policy.close_hour:02d}:00) 내에서 "
                f"{policy.slot_minutes}분 단위로 선택하세요.",
                "INVALID_TIME_RANGE",
            )
