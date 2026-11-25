"""Reservation Router — US-05·06·09 (Sprint 1) · US-19 퇴실 (Sprint 2)."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.clock import Clock, get_clock
from app.core.csrf import verify_csrf
from app.core.database import get_db
from app.core.deps import require_student
from app.models import ReservationStatus, User
from app.schemas.reservation import (
    ReservationCancelRequest,
    ReservationCreateRequest,
    ReservationListResponse,
    ReservationResponse,
)
from app.services.reservation_service import ReservationService

router = APIRouter(prefix="/api", tags=["reservations"])


def get_reservation_service(
    db: Session = Depends(get_db), clock: Clock = Depends(get_clock)
) -> ReservationService:
    return ReservationService(db, clock)


@router.post(
    "/reservations", response_model=ReservationResponse, dependencies=[Depends(verify_csrf)]
)
def create_reservation(
    req: ReservationCreateRequest,
    user: User = Depends(require_student),
    svc: ReservationService = Depends(get_reservation_service),
):
    # 설계서: 성공 200, 충돌 409
    return svc.create(user, req)


@router.get("/me/reservations", response_model=ReservationListResponse)
def my_reservations(
    status: ReservationStatus | None = Query(default=None),
    user: User = Depends(require_student),
    svc: ReservationService = Depends(get_reservation_service),
):
    return svc.list_mine(user, status)


@router.post(
    "/reservations/{reservation_id}/cancel",
    response_model=ReservationResponse,
    dependencies=[Depends(verify_csrf)],
)
def cancel_reservation(
    reservation_id: int,
    req: ReservationCancelRequest,
    user: User = Depends(require_student),
    svc: ReservationService = Depends(get_reservation_service),
):
    return svc.cancel_by_student(user, reservation_id, req)


# ───────────── Sprint 2 ─────────────
@router.post(
    "/reservations/{reservation_id}/checkout",
    response_model=ReservationResponse,
    dependencies=[Depends(verify_csrf)],
)
def checkout_reservation(
    reservation_id: int,
    user: User = Depends(require_student),
    svc: ReservationService = Depends(get_reservation_service),
):
    """US-19 퇴실 (설계서 4장 checkout, D-01, Backlog v1.2.0)."""
    return svc.checkout(user, reservation_id)
