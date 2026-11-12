from datetime import datetime

from sqlalchemy import DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models._types import str_enum
from app.models.enums import CancelOrigin


class NoShowEvent(Base):
    """Sprint 2 (US-10/11). reservation_id UNIQUE → 이중 노쇼 집계 방지."""

    __tablename__ = "no_show_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    reservation_id: Mapped[int] = mapped_column(ForeignKey("reservations.id"), unique=True)
    source: Mapped[CancelOrigin] = mapped_column(str_enum(CancelOrigin))
    occurred_at: Mapped[datetime] = mapped_column(DateTime)
    reset_at: Mapped[datetime | None] = mapped_column(DateTime)
