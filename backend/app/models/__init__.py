"""모든 엔티티를 여기서 import → Base.metadata에 등록된다 (설계서 3장 ERD)."""

from app.models.auth_session import AuthSession
from app.models.email_verification import EmailVerification
from app.models.enums import (
    OCCUPYING_STATUSES,
    AccountStatus,
    AdminCancelReason,
    CancelOrigin,
    ReservationStatus,
    RestrictionSource,
    Role,
    SeatViewStatus,
    StudentCancelReason,
)
from app.models.no_show_event import NoShowEvent
from app.models.operation_policy import OperationPolicy
from app.models.reservation import Reservation
from app.models.seat import Seat
from app.models.user import User
from app.models.user_restriction import UserRestriction

__all__ = [
    "OCCUPYING_STATUSES",
    "AccountStatus",
    "AdminCancelReason",
    "AuthSession",
    "CancelOrigin",
    "EmailVerification",
    "NoShowEvent",
    "OperationPolicy",
    "Reservation",
    "ReservationStatus",
    "RestrictionSource",
    "Role",
    "Seat",
    "SeatViewStatus",
    "StudentCancelReason",
    "User",
    "UserRestriction",
]
