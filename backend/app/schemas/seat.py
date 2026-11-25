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
    # Sprint 2 US-15: 관리자 정책 화면 초기값용 (설계서 GET /api/policies/current =
    # US-04·15). 기본값은 모델과 같음
    normal_days_ahead: int = 7
    normal_max_hours: int = 4
    exam_days_ahead: int = 1
    exam_max_hours: int = 3
    check_in_minutes: int = 15
    no_show_threshold: int = 3
    restriction_days: int = 3
    scheduler_minutes: int = 10


class SeatGridResponse(BaseModel):
    date: date
    start_at: datetime
    end_at: datetime
    policy: PolicyView  # FR-R-03: 시험 기간 최대 시간 UI 표시용
    seats: list[SeatView]
    # US-04 AC3 / D-28: 이 구간을 그대로 예약할 수 있는지 (진행 중·최대 시간 초과면 False)
    bookable: bool = True
    notice: str | None = None  # bookable=False일 때 화면에 보여줄 이유
