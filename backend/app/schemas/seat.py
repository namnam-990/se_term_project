"""US-04 DTO."""

from datetime import date, datetime

from pydantic import BaseModel

from app.models import SeatViewStatus
from app.schemas.common import ORMModel


class SeatView(ORMModel):
    seat_id: int
    seat_number: str
    grid_row: int
    grid_col: int
    status: SeatViewStatus


class PolicyView(ORMModel):
    exam_mode: bool
    days_ahead: int
    max_hours: int
    open_hour: int
    close_hour: int
    slot_minutes: int


class SeatGridResponse(BaseModel):
    date: date
    start_at: datetime
    end_at: datetime
    policy: PolicyView  # FR-R-03: 시험 기간 최대 시간 UI 표시용
    seats: list[SeatView]
