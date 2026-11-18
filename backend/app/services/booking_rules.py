"""예약 시간 규칙 — 좌석 조회(US-04)와 예약 생성(US-05)이 함께 쓰는 단일 규칙 모듈.

DB 없이 동작하는 순수 함수라 단위 테스트로 경계값을 바로 검증할 수 있다.
명세서 FR-A-20 / 결정 기록 D-11(운영시간·단위), D-12(최대 시간=1건 기준), D-13(기간=시작일 기준).
모든 값은 OperationPolicy에서 읽는다 (명세서 4.1 — 하드코딩 금지).

    validate_view   (조회, US-04) : 정책 → 시간 범위 → 기간(진행 중 시간대 허용)
    validate_booking(예약, US-05) : 정책 → 시간 범위 → 기간(과거 시작 불가) → 최대 시간

검사 함수와 오류 코드
    check_policy     : 정책 값 이상(단위 0분 등) → 503 OPERATION_POLICY_UNAVAILABLE
    check_time_range : 시간대·순서·운영시간·단위 → 400 INVALID_TIME_RANGE
    check_window     : 과거 아님, 오늘~+N일      → 400 OUT_OF_BOOKING_WINDOW
    check_max_hours  : 1건 길이 ≤ 최대 시간      → 400 EXCEEDS_MAX_HOURS

조회와 예약의 의도된 차이는 '기간' 하나뿐이다.
    조회: 이미 시작했지만 아직 끝나지 않은 시간대는 볼 수 있다 (지금 '사용 중'인 좌석 확인)
    예약: 시작 시각이 지났으면 예약할 수 없다
"""

from datetime import datetime, timedelta

from app.core.exceptions import BadRequestError, ServiceUnavailableError
from app.models import OperationPolicy


def check_policy(policy: OperationPolicy) -> None:
    """정책이 잘못 저장돼 있으면 계산 중 오류(0으로 나누기 등) 대신 503으로 안내."""
    if not (
        0 <= policy.open_hour < policy.close_hour <= 24
        and 0 < policy.slot_minutes <= (policy.close_hour - policy.open_hour) * 60
        and policy.days_ahead >= 0
        and policy.max_hours > 0
    ):
        raise ServiceUnavailableError(
            "운영 정책의 시간 설정이 올바르지 않습니다. 관리자에게 문의하세요.",
            code="OPERATION_POLICY_UNAVAILABLE",
        )


def check_time_range(start_at: datetime, end_at: datetime, policy: OperationPolicy) -> None:
    # 시간대(+09:00 등)가 붙은 값은 거부 — DB·Clock은 KST naive 기준이라 섞이면 비교 자체가 불가
    if start_at.tzinfo is not None or end_at.tzinfo is not None:
        raise BadRequestError(
            "시간대 정보 없이 한국 시간으로 입력하세요. (예: 2026-11-20T10:00:00)",
            code="INVALID_TIME_RANGE",
        )
    if start_at >= end_at:
        raise BadRequestError("종료 시각은 시작 시각보다 늦어야 합니다.", code="INVALID_TIME_RANGE")

    # '시작일 0시로부터 지난 시간'으로 비교 → close_hour=24(자정 종료)도 처리 가능
    day_start = start_at.replace(hour=0, minute=0, second=0, microsecond=0)
    start_offset, end_offset = start_at - day_start, end_at - day_start
    opens, closes = timedelta(hours=policy.open_hour), timedelta(hours=policy.close_hour)
    if start_offset < opens or end_offset > closes:
        raise BadRequestError(
            f"운영 시간({policy.open_hour:02d}:00~{policy.close_hour:02d}:00) 안에서만 "
            "선택할 수 있습니다.",
            code="INVALID_TIME_RANGE",
        )
    # 단위는 운영 시작 시각 기준으로 정렬 (예: 09시 시작·90분 단위 → 09:00, 10:30, 12:00 …)
    slot = timedelta(minutes=policy.slot_minutes)
    if (start_offset - opens) % slot or (end_offset - opens) % slot:
        raise BadRequestError(
            f"{policy.slot_minutes}분 단위로만 선택할 수 있습니다.", code="INVALID_TIME_RANGE"
        )


def check_window(
    start_at: datetime,
    end_at: datetime,
    now: datetime,
    policy: OperationPolicy,
    *,
    allow_in_progress: bool = False,
) -> None:
    """예약 가능 기간: 오늘 ~ 오늘+N일 (시작일 기준, 양 끝 포함, D-13).

    allow_in_progress=True (조회): 끝나지 않은 시간대면 허용
    allow_in_progress=False(예약): 시작 시각이 지났으면 거부
    """
    action = "조회" if allow_in_progress else "예약"
    if allow_in_progress and end_at <= now:
        raise BadRequestError(
            "이미 끝난 시간대는 조회할 수 없습니다.", code="OUT_OF_BOOKING_WINDOW"
        )
    if not allow_in_progress and start_at < now:
        raise BadRequestError("이미 지난 시간은 예약할 수 없습니다.", code="OUT_OF_BOOKING_WINDOW")

    last_day = now.date() + timedelta(days=policy.days_ahead)
    if start_at.date() > last_day:
        period = "당일~다음 날" if policy.exam_mode else f"오늘부터 {policy.days_ahead}일 후"
        raise BadRequestError(
            f"{period}({last_day:%m월 %d일})까지만 {action}할 수 있습니다.",
            code="OUT_OF_BOOKING_WINDOW",
        )


def check_max_hours(start_at: datetime, end_at: datetime, policy: OperationPolicy) -> None:
    if end_at - start_at > timedelta(hours=policy.max_hours):
        prefix = "시험 기간에는 " if policy.exam_mode else ""
        raise BadRequestError(
            f"{prefix}최대 {policy.max_hours}시간까지 예약할 수 있습니다.",
            code="EXCEEDS_MAX_HOURS",
        )


def validate_view(
    start_at: datetime, end_at: datetime, now: datetime, policy: OperationPolicy
) -> None:
    """US-04 좌석 조회 구간 검사. 최대 시간은 보지 않는다 (넓은 구간 조회 허용)."""
    check_policy(policy)
    check_time_range(start_at, end_at, policy)
    check_window(start_at, end_at, now, policy, allow_in_progress=True)


def validate_booking(
    start_at: datetime, end_at: datetime, now: datetime, policy: OperationPolicy
) -> None:
    """US-05 예약 생성 구간 검사."""
    check_policy(policy)
    check_time_range(start_at, end_at, policy)
    check_window(start_at, end_at, now, policy)
    check_max_hours(start_at, end_at, policy)
