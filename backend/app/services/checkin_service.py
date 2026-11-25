"""CheckInService — US-08 예약 시작 15분 이내 QR 체크인 (FR-C-02·03). Sprint 2 스켈레톤.

담당: US-08 담당자 (sprint2-plan.md)
설계서 Core Flow 2: "도서관 단말 또는 웹/앱 카메라로 스캔하며, 본인·토큰·RESERVED·시작 후
  15분 이내를 검증"

결정
- D-30: 학생이 가진 QR을 **도서관 단말기**(관리자 계정으로 띄운 /kiosk 화면)가 스캔.
  그래서 요청자는 단말기(관리자)이고, 설계서의 '본인' 검증은 "본인에게만 발급된 QR 토큰을
    가졌는가"로 확인.
- D-31: 단말기 카메라 스캔만. 코드 직접 입력·학생 앱 카메라는 구현하지 않음.
- D-32: 체크인 가능 = 시작 ≤ 지금 < 시작 + check_in_minutes (D-14·D-26과 같은 반열린 구간)
- D-36: 잠금 순서 회원 → 좌석 → 예약. 체크인은 회원 값을 바꾸지 않으므로 **예약 행만** 잠근다.
  노쇼 스케줄러(회원 → 예약)와 동시에 와도 예약 잠금 + 상태 재확인으로 하나만 확정.
- D-51: 이용 제한 중인 학생도 기존 예약 체크인은 허용 (제한은 새 예약 생성만 막음).
"""

from sqlalchemy.orm import Session

from app.core.clock import Clock
from app.models import Reservation


class CheckInService:
    def __init__(self, db: Session, clock: Clock):
        self.db, self.clock = db, clock

    def check_in(self, reservation_id: int, token: str) -> Reservation:
        """US-08 AC1~3.

        with transaction(db):
          1. reservation_repository.lock_by_id → 없으면 404 RESERVATION_NOT_FOUND
          2. 토큰 검증: hmac.compare_digest(token, qr_service.qr_token(reservation_id)) →
            틀리면 400 INVALID_QR
             (토큰은 예약 ID로 다시 계산되므로 학생이 QR 화면을 먼저 열지 않았어도 검증 가능, D-29)
          3. 상태: CHECKED_IN이면 409 ALREADY_CHECKED_IN, RESERVED가 아니면 409
            RESERVATION_NOT_ACTIVE
          4. 시간: now < start_at 또는 now ≥ start_at + check_in_minutes → 409 CHECKIN_WINDOW
             (안내: "체크인은 예약 시작부터 15분 이내에만 가능합니다." — 분은 정책 값)
          5. status = CHECKED_IN, checked_in_at = now
        반환한 예약은 ReservationResponse로 변환된다.
        """
        raise NotImplementedError("US-08 체크인")
