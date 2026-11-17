from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Reservation, ReservationStatus, Seat


def list_for_student(db: Session, user_id: int, status: ReservationStatus | None):
    statement = (
        select(Reservation, Seat.seat_number)
        .join(Seat, Reservation.seat_id == Seat.id)
        .where(Reservation.user_id == user_id)
        .order_by(Reservation.created_at.desc(), Reservation.id.desc())
    )
    if status is not None:
        statement = statement.where(Reservation.status == status)
    return db.execute(statement).all()
