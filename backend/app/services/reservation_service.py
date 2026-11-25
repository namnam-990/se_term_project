"""ReservationService — US-05 예약 생성(동시성 제어) / US-06 내역 조회 / US-09 직접 취소.

담당: 조성민 (US-05·09) / US-06은 sprint1-plan.md 담당자
설계서 Core Flow 1(좌석 예약 및 동시성 제어), Data Integrity Rules, Business Rules 참고.
"""

from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.core.clock import Clock
from app.core.database import transaction
from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError
from app.models import CancelOrigin, Reservation, ReservationStatus, User
from app.repositories import (
    reservation_repository,
    restriction_repository,
    seat_repository,
    user_repository,
)
from app.schemas.reservation import (
    ReservationCancelRequest,
    ReservationCreateRequest,
    ReservationListResponse,
    ReservationResponse,
)
from app.services.booking_rules import validate_booking
from app.services.policy_service import PolicyService


class ReservationService:
    def __init__(self, db: Session, clock: Clock):
        self.db, self.clock = db, clock

    # ──────────────────────────── US-05 예약 생성 ────────────────────────────
    def create(self, user: User, req: ReservationCreateRequest) -> Reservation:
        """US-05 (Core Flow 1) — FR-R-10 ~ 13, 명세서 4.4 트랜잭션 잠금

        한 트랜잭션 안에서:
          ① 회원 행 FOR UPDATE   → 같은 학생의 동시 요청을 한 줄로 세움 (FR-R-11 중복 방지)
          ② request_key 확인     → 같은 요청 재전송이면 기존 예약 반환
          ③ 이용 제한 확인        → 403 USER_RESTRICTED + 해제일 (FR-R-12)
          ④ 정책 검증            → 400 (FR-A-20, D-11·12·13·25)
          ⑤ 좌석 행 FOR UPDATE   → 같은 좌석의 동시 요청을 한 줄로 세움 (AC2)
          ⑥ 잠금 '후' 겹침 재검사 → 409 USER_TIME_OVERLAP / SEAT_ALREADY_RESERVED
          ⑦ RESERVED 저장 → 커밋 (FR-R-13)
        실패하면 transaction()이 롤백한다.

        왜 잠금 '후'에 검사하나: 잠금 전에 "비어 있다"고 확인하면, 확인과 저장 사이에
        다른 요청이 끼어들어 둘 다 저장될 수 있다(TOCTOU). 좌석 행을 잠근 뒤에 다시 보면
        앞 요청이 커밋한 예약이 보이므로(READ COMMITTED) 한 건만 성공한다.

        왜 회원 → 좌석 순서인가: 모든 요청이 같은 순서로 잠가야 서로 기다리다 멈추는
        교착 상태(deadlock)가 생기지 않는다. 체크인·자동 취소(Sprint 2)도 같은 순서를 따른다.
        """
        now = self.clock.now()
        with transaction(self.db):
            # ① 회원 잠금
            user_repository.lock_by_id(self.db, user.id)

            # ② 같은 요청 재전송 (더블 클릭·네트워크 재시도)
            if req.request_key:
                existing = reservation_repository.find_by_request_key(self.db, req.request_key)
                if existing is not None:
                    if existing.user_id != user.id:
                        raise ConflictError(
                            "이미 사용된 요청 키입니다.", code="REQUEST_KEY_CONFLICT"
                        )
                    return existing

            # ③ 이용 제한 (FR-R-12)
            restriction = restriction_repository.find_active(self.db, user.id, now)
            if restriction is not None:
                raise ForbiddenError(
                    f"이용 제한 중이라 예약할 수 없습니다. "
                    f"해제일: {restriction.ends_at:%Y-%m-%d %H:%M}",
                    code="USER_RESTRICTED",
                    extra={"restricted_until": restriction.ends_at.isoformat()},
                )

            # ④ 정책 (기간·최대 시간·운영시간·단위)
            policy = PolicyService(self.db).current()
            validate_booking(req.start_at, req.end_at, now, policy)

            # ⑤ 좌석 잠금
            seat = seat_repository.lock_by_id(self.db, req.seat_id)
            if seat is None or not seat.enabled:
                raise NotFoundError(
                    "존재하지 않거나 운영하지 않는 좌석입니다.", code="SEAT_NOT_FOUND"
                )

            # ⑥ 잠금 후 겹침 재검사 — 학생 먼저(AC3), 그다음 좌석(AC2)
            if reservation_repository.exists_overlap_for_user(
                self.db, user.id, req.start_at, req.end_at
            ):
                raise ConflictError(
                    "같은 시간대에 이미 예약한 좌석이 있습니다.", code="USER_TIME_OVERLAP"
                )
            if reservation_repository.exists_overlap_for_seat(
                self.db, seat.id, req.start_at, req.end_at
            ):
                raise ConflictError(
                    "이미 선택된 좌석입니다. 다른 좌석을 선택해 주세요.",
                    code="SEAT_ALREADY_RESERVED",
                )

            # ⑦ 저장
            reservation = Reservation(
                user_id=user.id,
                seat_id=seat.id,
                seat=seat,  # 응답의 seat_number용 (커밋 후 추가 조회 방지)
                start_at=req.start_at,
                end_at=req.end_at,
                status=ReservationStatus.RESERVED,
                request_key=req.request_key,
            )
            reservation_repository.add(self.db, reservation)
        return reservation

    # ──────────────────────────── US-06 내역 조회 ────────────────────────────
    def list_mine(self, user: User, status: ReservationStatus | None) -> ReservationListResponse:
        reservations = reservation_repository.list_by_user(self.db, user.id, status)
        return ReservationListResponse(
            items=[ReservationResponse.model_validate(item) for item in reservations],
            message=None
            if reservations
            else ("선택한 상태의 예약이 없습니다." if status else "예약 내역이 없습니다."),
        )

    # ──────────────────────────── US-09 직접 취소 ────────────────────────────
    def cancel_by_student(
        self, user: User, reservation_id: int, req: ReservationCancelRequest
    ) -> Reservation:
        """US-09 — FR-X-01 ~ 04

        - 예약 행 FOR UPDATE: Sprint 2의 체크인·노쇼 자동 취소와 동시에 일어나도 하나만 확정
        - 없음 → 404 RESERVATION_NOT_FOUND / 본인 아님 → 403 NOT_OWNER (명세 4.5)
        - RESERVED가 아님(체크인 완료·취소됨) → 409 NOT_CANCELLABLE (AC3)
        - 체크인 마감(시작 + 15분)이 지난 RESERVED → 409 NOT_CANCELLABLE (D-26)
          : 이미 노쇼가 확정된 시점이라, 스케줄러(10분 주기)가 돌기 전에 취소해서
            패널티를 피하는 것을 막는다. 마감 전 '체크인 대기'는 취소 허용 (FR-X-01, D-14)
        - CANCELLED + 사유 + cancel_origin=STUDENT + penalty_applied=False (FR-X-02·03)
        - 좌석은 상태가 CANCELLED가 되는 순간 겹침 검사 대상에서 빠지므로 즉시 가용 (FR-X-04)
        - no_show_count는 건드리지 않는다 (FR-X-03)
        """
        now = self.clock.now()
        with transaction(self.db):
            reservation = reservation_repository.lock_by_id(self.db, reservation_id)
            if reservation is None:
                raise NotFoundError("예약을 찾을 수 없습니다.", code="RESERVATION_NOT_FOUND")
            if reservation.user_id != user.id:
                raise ForbiddenError("본인의 예약만 취소할 수 있습니다.", code="NOT_OWNER")
            if reservation.status != ReservationStatus.RESERVED:
                raise ConflictError(
                    "체크인 완료되었거나 이미 취소된 예약은 취소할 수 없습니다.",
                    code="NOT_CANCELLABLE",
                )
            policy = PolicyService(self.db).current()
            deadline = reservation.start_at + timedelta(minutes=policy.check_in_minutes)
            if now >= deadline:
                raise ConflictError(
                    f"체크인 마감({deadline:%H:%M})이 지나 취소할 수 없습니다.",
                    code="NOT_CANCELLABLE",
                )

            reservation.status = ReservationStatus.CANCELLED
            reservation.cancel_reason = req.reason.value
            reservation.cancel_detail = req.detail
            reservation.cancel_origin = CancelOrigin.STUDENT
            reservation.cancelled_by = user.id
            reservation.cancelled_at = now
            reservation.penalty_applied = False
        return reservation

    # ──────────────────────────── US-19 퇴실 (Sprint 2) ────────────────────────────
    def checkout(self, user: User, reservation_id: int) -> Reservation:
        """US-19 이용 종료(퇴실) — 설계서 4장 checkout, D-01, Backlog v1.2.0 (D-47)

        with transaction(db):
          1. reservation_repository.lock_by_id (예약만 잠금 — 회원 값을 바꾸지 않음, D-36)
          2. 없으면 404 RESERVATION_NOT_FOUND / 본인 아니면 403 NOT_OWNER (AC3)
          3. CHECKED_IN이 아니면 409 NOT_CHECKOUTABLE ("체크인한 예약만 퇴실할 수 있습니다.") (AC2)
          4. status = COMPLETED, ended_at = now (AC1)
        - 좌석: COMPLETED는 겹침 검사 대상(RESERVED·CHECKED_IN)이 아니므로 즉시 가용 (AC1)
        - 노쇼 카운터는 건드리지 않음 (AC4, 설계서 "본인 퇴실은 노쇼를 부과하지 않는다")
        - 이용 제한 중이어도 퇴실 가능 (D-51)
        """
        raise NotImplementedError("US-19 퇴실")

    def _now(self) -> datetime:
        return self.clock.now()
