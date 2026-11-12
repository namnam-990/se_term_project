from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models._types import str_enum
from app.models.enums import RestrictionSource


class UserRestriction(Base):
    """이용 제한 이력. 활성 제한 = starts_at <= now < ends_at AND released_at IS NULL.

    Sprint 1(US-05)은 '활성 제한이 있으면 예약 거부 + 해제일 안내'만 사용.
    생성(노쇼 자동/관리자 수동)은 Sprint 2.
    """

    __tablename__ = "user_restrictions"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    source: Mapped[RestrictionSource] = mapped_column(str_enum(RestrictionSource))
    starts_at: Mapped[datetime] = mapped_column(DateTime)
    ends_at: Mapped[datetime] = mapped_column(DateTime)
    released_at: Mapped[datetime | None] = mapped_column(DateTime)
    reason: Mapped[str | None] = mapped_column(String(200))
