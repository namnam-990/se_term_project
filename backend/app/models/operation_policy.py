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
    # 운영 시간·예약 단위 (D-11, 11/18 개정) — 1층 운영시간 06:00~23:00, 30분 단위
    # 24시간 운영은 날짜 경계 처리가 복잡해지고 명세서 정책 범위를 벗어나 제외
    open_hour: Mapped[int] = mapped_column(Integer, default=6)
    close_hour: Mapped[int] = mapped_column(Integer, default=23)
    slot_minutes: Mapped[int] = mapped_column(Integer, default=30)

    @property
    def days_ahead(self) -> int:
        return self.exam_days_ahead if self.exam_mode else self.normal_days_ahead

    @property
    def max_hours(self) -> int:
        return self.exam_max_hours if self.exam_mode else self.normal_max_hours
