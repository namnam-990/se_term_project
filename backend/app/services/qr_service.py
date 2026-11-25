"""QrService — US-07 체크인용 QR 발급 (FR-C-01). Sprint 2 스켈레톤.

담당: US-07 담당자 (sprint2-plan.md)
설계서 Core Flow 2: "QR에 예약 좌석 정보를 담고 본인에게만 발급한다."

결정
- D-29: QR 내용 = 예약 ID + 좌석 번호 + 토큰. DB에는 토큰 해시(qr_token_hash)만 저장.
  토큰은 서버 비밀키로 만든 HMAC이라 **예약마다 항상 같은 값**이다.
  → 다시 열어도 같은 QR (D-33 재발급 없음), 원문을 DB에 저장하지 않아도 되고,
    비밀키 없이는 위조할 수 없다.
- D-33: RESERVED일 때만 QR 표시(active=True). 그 외 상태는 active=False + 안내.
- 타인 예약 → 403 NOT_OWNER, 없으면 404 RESERVATION_NOT_FOUND (US-07 AC3).

아래 토큰·payload 함수는 US-07(발급)과 US-08(체크인)이 같이 쓰는 **약속(계약)**이라 미리 구현해 둠.
바꾸려면 두 담당자가 같이 정하고 docs/api-contract.md도 함께 수정.
"""

import hashlib
import hmac

from sqlalchemy.orm import Session

from app.core.clock import Clock
from app.core.config import get_settings
from app.core.security import sha256
from app.models import User
from app.schemas.checkin import QrResponse

PAYLOAD_PREFIX = "LSRS"


def qr_token(reservation_id: int) -> str:
    """예약별 고정 토큰 = HMAC-SHA256(비밀키, "qr:<예약ID>") 앞 32자 (D-29)."""
    key = get_settings().jwt_secret_key.encode()
    digest = hmac.new(key, f"qr:{reservation_id}".encode(), hashlib.sha256).hexdigest()
    return digest[:32]


def qr_token_hash(reservation_id: int) -> str:
    """Reservation.qr_token_hash에 저장할 값 (원문 대신 해시만, Sprint 1 인증 코드와 같은 방식)."""
    return sha256(qr_token(reservation_id))


def build_payload(reservation_id: int, seat_number: str) -> str:
    """QR에 인코딩할 문자열: "LSRS|r=12|seat=A-01|t=<토큰>" (명세 FR-C-01 '좌석 정보 인코딩')."""
    return f"{PAYLOAD_PREFIX}|r={reservation_id}|seat={seat_number}|t={qr_token(reservation_id)}"


def parse_payload(text: str) -> tuple[int, str] | None:
    """단말기가 읽은 QR 문자열 → (예약 ID, 토큰). 형식이 틀리면 None (US-08 AC2 '유효하지
    않은 코드')."""
    parts = text.strip().split("|")
    if len(parts) != 4 or parts[0] != PAYLOAD_PREFIX:
        return None
    fields = dict(p.split("=", 1) for p in parts[1:] if "=" in p)
    if not fields.get("r", "").isdigit() or not fields.get("t"):
        return None
    return int(fields["r"]), fields["t"]


class QrService:
    def __init__(self, db: Session, clock: Clock):
        self.db, self.clock = db, clock

    def get_qr(self, user: User, reservation_id: int) -> QrResponse:
        """US-07 AC1~3.

        1. 예약 조회 → 없으면 404 RESERVATION_NOT_FOUND, 본인 아니면 403 NOT_OWNER
        2. RESERVED가 아니면 active=False, message="사용할 수 없는 예약입니다." (payload·svg 없음)
        3. RESERVED면: qr_token_hash가 비어 있으면 저장 (transaction 사용)
           payload = build_payload(...), svg = segno로 만든 SVG 문자열
           (segno.make(payload).svg_inline(scale=...) 등 — segno 문서 참고)
        """
        raise NotImplementedError("US-07 QR 발급")
