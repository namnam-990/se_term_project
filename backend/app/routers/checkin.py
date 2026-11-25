"""CheckIn Router — US-07 QR 발급 · US-08 체크인 (Sprint 2). 설계서 4장 API.

- GET  /api/reservations/{id}/qr        학생 본인 (US-07)
- POST /api/reservations/{id}/check-in  체크인 단말 = 관리자 로그인 화면 (US-08, D-30 해석)
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.clock import Clock, get_clock
from app.core.csrf import verify_csrf
from app.core.database import get_db
from app.core.deps import require_admin, require_student
from app.models import User
from app.schemas.checkin import CheckInRequest, QrResponse
from app.schemas.reservation import ReservationResponse
from app.services.checkin_service import CheckInService
from app.services.qr_service import QrService

router = APIRouter(prefix="/api/reservations", tags=["check-in"])


@router.get("/{reservation_id}/qr", response_model=QrResponse)
def get_qr(
    reservation_id: int,
    user: User = Depends(require_student),
    db: Session = Depends(get_db),
    clock: Clock = Depends(get_clock),
):
    return QrService(db, clock).get_qr(user, reservation_id)


@router.post(
    "/{reservation_id}/check-in",
    response_model=ReservationResponse,
    dependencies=[Depends(verify_csrf)],
)
def check_in(
    reservation_id: int,
    req: CheckInRequest,
    _terminal: User = Depends(require_admin),
    db: Session = Depends(get_db),
    clock: Clock = Depends(get_clock),
):
    return CheckInService(db, clock).check_in(reservation_id, req.token)
