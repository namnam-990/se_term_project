from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Index, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models._types import str_enum
from app.models.enums import CancelOrigin, ReservationStatus


class Reservation(Base):
    __tablename__ = "reservations"
    __table_args__ = (
        CheckConstraint("start_at < end_at", name="ck_reservation_time_order"),
        # 겹침 검사용 인덱스 (설계서: 시간 겹침 = 기존.start < 요청.end AND 기존.end > 요청.start)
        Index("ix_reservation_seat_time", "seat_id", "start_at", "end_at"),
        Index("ix_reservation_user_time", "user_id", "start_at", "end_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    seat_id: Mapped[int] = mapped_column(ForeignKey("seats.id"))
    start_at: Mapped[datetime] = mapped_column(DateTime)
    end_at: Mapped[datetime] = mapped_column(DateTime)
    status: Mapped[ReservationStatus] = mapped_column(
        str_enum(ReservationStatus), default=ReservationStatus.RESERVED
    )
    checked_in_at: Mapped[datetime | None] = mapped_column(DateTime)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime)
    cancel_reason: Mapped[str | None] = mapped_column(String(30))
    cancel_detail: Mapped[str | None] = mapped_column(String(200))  # '기타' 상세
    cancel_origin: Mapped[CancelOrigin | None] = mapped_column(str_enum(CancelOrigin))
    cancelled_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime)
    penalty_applied: Mapped[bool] = mapped_column(Boolean, default=False)
    qr_token_hash: Mapped[str | None] = mapped_column(String(64))  # Sprint 2
    # 같은 요청 재전송(더블 클릭 등) 시 중복 생성 방지
    request_key: Mapped[str | None] = mapped_column(String(64), unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    user = relationship("User", foreign_keys=[user_id])
    seat = relationship("Seat")
