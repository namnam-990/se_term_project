"""예약 시간 규칙 — DB 없이 동작하는 순수 함수 (US-04 조회 · US-05 예약 공용).

명세서 FR-A-20 / 결정 기록 D-11(운영시간·단위), D-12(최대 시간=1건 기준), D-13(기간=시작일 기준).
모든 값은 OperationPolicy에서 읽는다 (명세서 4.1 — 하드코딩 금지).

검사 순서와 오류 코드
    1) check_time_range : 시간대 없음, 시작<종료, 운영시간 안, 60분 정시 → INVALID_TIME_RANGE
    2) check_window     : 과거 아님, 오늘~오늘+N일(양 끝 포함)       → OUT_OF_BOOKING_WINDOW
    3) check_max_hours  : 예약 1건 길이 ≤ 최대 시간                 → EXCEEDS_MAX_HOURS
    (모두 400)
"""

from datetime import datetime, timedelta

from app.core.exceptions import BadRequestError
from app.models import OperationPolicy


def _on_slot(t: datetime, slot_minutes: int) -> bool:
    return t.second == 0 and t.microsecond == 0 and (t.hour * 60 + t.minute) % slot_minutes == 0


def check_time_range(start_at: datetime, end_at: datetime, policy: OperationPolicy) -> None:
    # 시간대(+09:00 등)가 붙은 값은 거부 — DB·Clock은 KST naive 기준이라 섞이면 비교 자체가 불가
    if start_at.tzinfo is not None or end_at.tzinfo is not None:
        raise BadRequestError(
            "시간대 정보 없이 한국 시간으로 입력하세요. (예: 2026-11-20T10:00:00)",
            code="INVALID_TIME_RANGE",
        )
    if start_at >= end_at:
        raise BadRequestError("종료 시각은 시작 시각보다 늦어야 합니다.", code="INVALID_TIME_RANGE")

    # 운영 시간은 '시작일 0시로부터의 경과 시간'으로 비교 → close_hour=24(자정 종료)도 처리 가능
    day_start = start_at.replace(hour=0, minute=0, second=0, microsecond=0)
    start_offset, end_offset = start_at - day_start, end_at - day_start
    if start_offset < timedelta(hours=policy.open_hour) or end_offset > timedelta(
        hours=policy.close_hour
    ):
        raise BadRequestError(
            f"운영 시간({policy.open_hour:02d}:00~{policy.close_hour:02d}:00) 안에서만 "
            "예약할 수 있습니다.",
            code="INVALID_TIME_RANGE",
        )
    if not (_on_slot(start_at, policy.slot_minutes) and _on_slot(end_at, policy.slot_minutes)):
        raise BadRequestError(
            f"예약은 {policy.slot_minutes}분 단위로만 할 수 있습니다.", code="INVALID_TIME_RANGE"
        )


def check_window(start_at: datetime, now: datetime, policy: OperationPolicy) -> None:
    if start_at < now:
        raise BadRequestError("이미 지난 시간은 예약할 수 없습니다.", code="OUT_OF_BOOKING_WINDOW")
    last_day = now.date() + timedelta(days=policy.days_ahead)
    if start_at.date() > last_day:
        period = "당일~다음 날" if policy.exam_mode else f"오늘부터 {policy.days_ahead}일 후"
        raise BadRequestError(
            f"{period}({last_day:%m월 %d일})까지만 예약할 수 있습니다.",
            code="OUT_OF_BOOKING_WINDOW",
        )


def check_max_hours(start_at: datetime, end_at: datetime, policy: OperationPolicy) -> None:
    if end_at - start_at > timedelta(hours=policy.max_hours):
        prefix = "시험 기간에는 " if policy.exam_mode else ""
        raise BadRequestError(
            f"{prefix}최대 {policy.max_hours}시간까지 예약할 수 있습니다.",
            code="EXCEEDS_MAX_HOURS",
        )


def validate_booking(
    start_at: datetime, end_at: datetime, now: datetime, policy: OperationPolicy
) -> None:
    """US-05 예약 생성 시 전체 검사."""
    check_time_range(start_at, end_at, policy)
    check_window(start_at, now, policy)
    check_max_hours(start_at, end_at, policy)
