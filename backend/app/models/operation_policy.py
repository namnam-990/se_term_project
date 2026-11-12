from sqlalchemy import Boolean, Integer
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class OperationPolicy(Base):
    """운영 정책 (요구사항 4.1: 하드코딩 금지, DB 파라미터로 관리). 단일 행(id=1) 사용.

    Sprint 1에서는 읽기만 한다(좌석 조회·예약 검증). 수정 API는 Sprint 2 (US-15).
    """

    __tablename__ = "operation_policies"

    id: Mapped[int] = mapped_column(primary_key=True)
    exam_mode: Mapped[bool] = mapped_column(Boolean, default=False)
    normal_days_ahead: Mapped[int] = mapped_column(Integer, default=7)  # 오늘 ~ +7일
    normal_max_hours: Mapped[int] = mapped_column(Integer, default=4)
    exam_days_ahead: Mapped[int] = mapped_column(Integer, default=1)  # 당일 ~ 다음 날
    exam_max_hours: Mapped[int] = mapped_column(Integer, default=3)
    check_in_minutes: Mapped[int] = mapped_column(Integer, default=15)
    no_show_threshold: Mapped[int] = mapped_column(Integer, default=3)
    restriction_days: Mapped[int] = mapped_column(Integer, default=3)
    scheduler_minutes: Mapped[int] = mapped_column(Integer, default=10)
    # 운영 시간 (예약 시간 단위 검증용) — 팀 합의로 변경 가능
    open_hour: Mapped[int] = mapped_column(Integer, default=9)
    close_hour: Mapped[int] = mapped_column(Integer, default=22)
    slot_minutes: Mapped[int] = mapped_column(Integer, default=60)

    @property
    def days_ahead(self) -> int:
        return self.exam_days_ahead if self.exam_mode else self.normal_days_ahead

    @property
    def max_hours(self) -> int:
        return self.exam_max_hours if self.exam_mode else self.normal_max_hours
