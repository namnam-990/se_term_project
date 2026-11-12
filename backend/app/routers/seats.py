"""Seat Router — US-04."""

from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.clock import Clock, get_clock
from app.core.database import get_db
from app.core.deps import require_student
from app.models import User
from app.schemas.seat import SeatGridResponse
from app.services.seat_query_service import SeatQueryService

router = APIRouter(prefix="/api/seats", tags=["seats"])


def get_seat_query_service(
    db: Session = Depends(get_db), clock: Clock = Depends(get_clock)
) -> SeatQueryService:
    return SeatQueryService(db, clock)


@router.get("", response_model=SeatGridResponse)
def get_seats(
    start_at: datetime = Query(..., examples=["2026-11-20T10:00:00"]),
    end_at: datetime = Query(..., examples=["2026-11-20T12:00:00"]),
    user: User = Depends(require_student),
    svc: SeatQueryService = Depends(get_seat_query_service),
):
    return svc.get_grid(user, start_at, end_at)
