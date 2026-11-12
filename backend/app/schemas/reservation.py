"""US-05·06·09 DTO."""

from datetime import datetime

from pydantic import BaseModel, Field

from app.models import ReservationStatus, StudentCancelReason
from app.schemas.common import ORMModel


class ReservationCreateRequest(BaseModel):
    seat_id: int
    start_at: datetime = Field(examples=["2026-11-20T10:00:00"])
    end_at: datetime = Field(examples=["2026-11-20T12:00:00"])
    request_key: str | None = Field(
        default=None, max_length=64, description="클라이언트 생성 UUID. 재전송 시 중복 생성 방지"
    )


class ReservationResponse(ORMModel):
    id: int
    seat_id: int
    seat_number: str
    start_at: datetime
    end_at: datetime
    status: ReservationStatus
    cancel_reason: str | None = None
    created_at: datetime | None = None


class ReservationListResponse(BaseModel):
    items: list[ReservationResponse]
    message: str | None = None  # 빈 결과 안내 (US-06 AC3)


class ReservationCancelRequest(BaseModel):
    reason: StudentCancelReason
    detail: str | None = Field(default=None, max_length=200)
