from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Reservation, Seat
from app.models.enums import OCCUPYING_STATUSES


def list_seats_with_overlaps(db: Session, start_at: datetime, end_at: datetime):
    overlaps = (
        (Reservation.seat_id == Seat.id)
        & (Reservation.start_at < end_at)
        & (Reservation.end_at > start_at)
        & Reservation.status.in_(OCCUPYING_STATUSES)
    )
    return db.execute(
        select(Seat, Reservation)
        .outerjoin(Reservation, overlaps)
        .where(Seat.enabled.is_(True))
        .order_by(Seat.grid_row, Seat.grid_col, Seat.id)
    ).all()
