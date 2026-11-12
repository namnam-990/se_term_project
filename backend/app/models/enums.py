"""도메인 Enum — 문자열 값은 DB와 API 응답에 그대로 쓰이므로 변경 시 팀 합의 필요."""

from enum import StrEnum


class Role(StrEnum):
    ROLE_STUDENT = "ROLE_STUDENT"
    ROLE_ADMIN = "ROLE_ADMIN"


class AccountStatus(StrEnum):
    PENDING = "PENDING"  # 이메일 인증 전 (FR-U-03)
    ACTIVE = "ACTIVE"  # 인증 완료 (FR-U-04)
    LOCKED = "LOCKED"  # 로그인 6번째 연속 실패 (FR-U-13, 시간 제한 없음)


class ReservationStatus(StrEnum):
    RESERVED = "RESERVED"  # 생성 시 (FR-R-13)
    CHECKED_IN = "CHECKED_IN"  # QR 체크인 (Sprint 2)
    CANCELLED = "CANCELLED"  # 학생 직접 / 관리자 강제 취소
    AUTO_CANCELLED = "AUTO_CANCELLED"  # 노쇼 자동 취소 (Sprint 2)
    COMPLETED = "COMPLETED"  # 퇴실 (문제정의서)


# 좌석을 점유하는 상태 (설계서 Data Integrity Rules)
OCCUPYING_STATUSES = (ReservationStatus.RESERVED, ReservationStatus.CHECKED_IN)


class CancelOrigin(StrEnum):
    STUDENT = "STUDENT"
    ADMIN = "ADMIN"
    SYSTEM = "SYSTEM"


class StudentCancelReason(StrEnum):  # FR-X-02
    SCHEDULE_CHANGE = "SCHEDULE_CHANGE"  # 일정 변경
    SEAT_CHANGE = "SEAT_CHANGE"  # 좌석 위치 변경
    TIME_CHANGE = "TIME_CHANGE"  # 시간대 변경
    OTHER = "OTHER"  # 기타


class AdminCancelReason(StrEnum):  # FR-X-21 (Sprint 2)
    FACILITY_CHECK = "FACILITY_CHECK"
    RULE_VIOLATION = "RULE_VIOLATION"
    SYSTEM_FIX = "SYSTEM_FIX"
    OTHER = "OTHER"


class RestrictionSource(StrEnum):
    AUTO_NO_SHOW = "AUTO_NO_SHOW"
    ADMIN = "ADMIN"


class SeatViewStatus(StrEnum):
    """좌석 조회 4상태 (FR-R-02) — DB 컬럼이 아니라 조회 시 계산값."""

    AVAILABLE = "AVAILABLE"  # 예약 가능
    IN_USE = "IN_USE"  # 사용 중 (타인 CHECKED_IN)
    MINE = "MINE"  # 내 예약
    RESERVED = "RESERVED"  # 예약됨 (타인 RESERVED)
