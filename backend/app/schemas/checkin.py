"""US-07 QR 발급 · US-08 체크인 DTO — 필드명은 docs/api-contract.md와 일치시킨다."""

from datetime import datetime

from pydantic import BaseModel, Field


class QrResponse(BaseModel):
    """GET /api/reservations/{id}/qr (US-07).

    active=True  : RESERVED → payload·svg로 QR 표시 (AC1)
    active=False : 취소·자동 취소·체크인 완료·이용 완료 → QR 없이 message만 (AC2, D-33)
    """

    reservation_id: int
    seat_number: str
    start_at: datetime
    end_at: datetime
    active: bool
    # D-29: QR에 담는 문자열 = "LSRS|r=<예약ID>|seat=<좌석번호>|t=<토큰>"
    payload: str | None = None
    svg: str | None = None  # 서버에서 만든 QR 이미지 (segno, SVG 문자열)
    message: str | None = None


class CheckInRequest(BaseModel):
    """POST /api/reservations/{id}/check-in (US-08) — 체크인 단말이 QR에서 읽은 토큰 (D-30)."""

    token: str = Field(min_length=1, max_length=128)
