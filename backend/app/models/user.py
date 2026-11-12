from datetime import datetime

from sqlalchemy import DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models._types import str_enum
from app.models.enums import AccountStatus, Role


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    # 학생은 login_id = student_no, 관리자는 관리자 ID (FR-U-10)
    login_id: Mapped[str] = mapped_column(String(50), unique=True)
    student_no: Mapped[str | None] = mapped_column(String(20), unique=True)
    email: Mapped[str | None] = mapped_column(String(255), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    name: Mapped[str | None] = mapped_column(String(50))
    role: Mapped[Role] = mapped_column(str_enum(Role), default=Role.ROLE_STUDENT)
    account_status: Mapped[AccountStatus] = mapped_column(
        str_enum(AccountStatus), default=AccountStatus.PENDING
    )
    failed_login_count: Mapped[int] = mapped_column(Integer, default=0)
    no_show_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
