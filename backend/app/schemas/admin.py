"""관리자 기능 DTO — US-11 ~ 17 (Sprint 2). 필드명은 docs/api-contract.md와 일치시킨다."""

from datetime import date, datetime
from enum import StrEnum

from pydantic import BaseModel, Field

from app.models import AccountStatus, AdminCancelReason, ReservationStatus, Role


# ───────────── US-11 강제 취소 ─────────────
class AdminCancelRequest(BaseModel):
    """FR-X-20~22. reason을 비우면 Service가 400 REASON_REQUIRED (US-11 AC3 안내 문구용으로
    Optional).

    사유와 패널티는 서로 독립 선택 (D-39).
    """

    reason: AdminCancelReason | None = None
    detail: str | None = Field(default=None, max_length=200)
    apply_penalty: bool = False


# ───────────── US-12 대시보드 ─────────────
class DashboardSeatStatus(StrEnum):
    """관리자 그리드 3상태 고정 (FR-A-02, Backlog US-12 AC2, 설계서 5장, D-42).

    학생 좌석 화면의 4상태(SeatViewStatus)와 다르다. 상태를 늘리지 말 것.
    """

    EMPTY = "EMPTY"  # 빈 좌석
    IN_USE = "IN_USE"  # 사용 중: CHECKED_IN이고 시작 ≤ 지금 < 종료 (퇴실 전)
    # 체크인 대기: RESERVED이고 시작 ≤ 지금 < 종료 (마감 지났지만 자동 취소 전 포함, D-14·D-34)
    WAITING = "WAITING"


class DashboardSeat(BaseModel):
    seat_id: int
    seat_number: str
    grid_row: int
    grid_col: int
    status: DashboardSeatStatus


class DashboardResponse(BaseModel):
    """설계서 5장 지표: 이용 인원 = 사용 중 수, 잔여 = 운영 좌석 − (사용 중 + 체크인 대기),
    가동률 = 사용 중 ÷ 운영 좌석 × 100 (운영 좌석 0이면 0%)."""

    as_of: datetime
    total_seats: int
    in_use: int
    waiting: int
    remaining: int
    utilization_rate: float
    seats: list[DashboardSeat]


# ───────────── US-13·14·17 학생 관리 ─────────────
class AdminReservationItem(BaseModel):
    """D-38: 강제 취소 대상을 찾기 위해 학생별 현재·예정 예약을 함께 보여준다."""

    id: int
    seat_number: str
    start_at: datetime
    end_at: datetime
    status: ReservationStatus


class AdminUserItem(BaseModel):
    id: int
    login_id: str
    student_no: str | None
    email: str | None
    name: str | None = None
    role: Role
    account_status: AccountStatus
    no_show_count: int
    restricted_until: datetime | None = None  # 활성 제한의 종료 시각 (없으면 None, D-51)
    reservations: list[AdminReservationItem] = []


class AdminUserListResponse(BaseModel):
    items: list[AdminUserItem]
    message: str | None = None  # 검색 결과 없음 안내 (US-13 AC3)


class RestrictionSetRequest(BaseModel):
    """US-14 AC1: 제한 일자. 그 날짜가 끝날 때(다음 날 00:00)까지 제한 (D-51)."""

    until: date
    reason: str | None = Field(default=None, max_length=200)


class RoleChangeRequest(BaseModel):
    """US-17: 관리자 권한 부여·회수. 본인 회수는 거부."""

    role: Role


# ───────────── US-15 정책 ─────────────
class PolicyUpdateRequest(BaseModel):
    """FR-A-20 + 명세서 4.1 정책 파라미터. 운영 시간·예약 단위(D-11)는 관리자 화면에서
    수정하지 않는다 (D-45).

    잘못된 값은 저장 전에 400 (Field 범위 검사). 변경은 새 예약부터 적용, 기존 예약 유지 (D-45).
    """

    exam_mode: bool
    normal_days_ahead: int = Field(ge=0, le=30)
    normal_max_hours: int = Field(ge=1, le=17)
    exam_days_ahead: int = Field(ge=0, le=30)
    exam_max_hours: int = Field(ge=1, le=17)
    check_in_minutes: int = Field(ge=1, le=60)
    no_show_threshold: int = Field(ge=1, le=10)
    restriction_days: int = Field(ge=1, le=30)


# ───────────── US-16 통계 (Could) ─────────────
class DailyRate(BaseModel):
    date: date
    utilization_rate: float


class HourlyRate(BaseModel):
    hour: int  # 0~23
    utilization_rate: float


class StatisticsResponse(BaseModel):
    """설계서 5장: 이용 좌석 분 ÷ 운영 가능 좌석 분 × 100, 이력 없으면 0%."""

    from_date: date
    to_date: date
    daily: list[DailyRate]
    hourly: list[HourlyRate]
    message: str | None = None
