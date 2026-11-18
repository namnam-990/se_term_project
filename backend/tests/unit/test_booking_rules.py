"""예약 시간 규칙 경계값 — DB 없이 순수 함수만 검사 (D-11·D-12·D-13, FR-A-20).

데모 '경계값' 케이스: pytest -v tests/unit/test_booking_rules.py
"""

from datetime import datetime

import pytest

from app.core.exceptions import BadRequestError, ServiceUnavailableError
from app.models import OperationPolicy
from app.services.booking_rules import validate_booking, validate_view

NOW = datetime(2026, 11, 20, 9, 0)  # 금요일 09:00


def policy(exam: bool = False) -> OperationPolicy:
    return OperationPolicy(
        exam_mode=exam,
        normal_days_ahead=7,
        normal_max_hours=4,
        exam_days_ahead=1,
        exam_max_hours=3,
        open_hour=9,
        close_hour=22,
        slot_minutes=60,
    )


def at(day: int, hour: int, minute: int = 0) -> datetime:
    return datetime(2026, 11, day, hour, minute)


@pytest.mark.parametrize(
    "start,end",
    [
        (at(20, 9), at(20, 13)),  # 운영 시작 시각 + 정확히 4시간
        (at(20, 18), at(20, 22)),  # 운영 종료 시각까지
        (at(27, 10), at(27, 11)),  # 오늘+7일 (마지막 허용일)
        (at(20, 9), at(20, 10)),  # 지금 시각에 시작
    ],
    ids=["4시간-정확히", "22시-종료", "+7일", "현재시각-시작"],
)
def test_allowed_boundaries(start, end):
    validate_booking(start, end, NOW, policy())


@pytest.mark.parametrize(
    "start,end,code",
    [
        (at(20, 12), at(20, 10), "INVALID_TIME_RANGE"),  # 역순
        (at(20, 10), at(20, 10), "INVALID_TIME_RANGE"),  # 0분
        (at(20, 21), at(21, 1), "INVALID_TIME_RANGE"),  # 날짜 넘김 (22시 종료 정책)
        (at(20, 8), at(20, 10), "INVALID_TIME_RANGE"),  # 운영 시작 전
        (at(20, 21), at(20, 23), "INVALID_TIME_RANGE"),  # 운영 종료 후
        (at(20, 10, 30), at(20, 12), "INVALID_TIME_RANGE"),  # 60분 단위 아님
        (at(19, 10), at(19, 12), "OUT_OF_BOOKING_WINDOW"),  # 어제
        (at(28, 10), at(28, 12), "OUT_OF_BOOKING_WINDOW"),  # 오늘+8일
        (at(20, 10), at(20, 15), "EXCEEDS_MAX_HOURS"),  # 5시간
    ],
    ids=["역순", "0분", "날짜넘김", "운영전", "운영후", "단위", "과거", "+8일", "5시간"],
)
def test_rejected(start, end, code):
    with pytest.raises(BadRequestError) as e:
        validate_booking(start, end, NOW, policy())
    assert e.value.code == code


def test_exam_mode_tomorrow_ok_day_after_rejected():
    validate_booking(at(21, 10), at(21, 13), NOW, policy(exam=True))  # 다음 날, 3시간
    with pytest.raises(BadRequestError) as e:
        validate_booking(at(22, 10), at(22, 11), NOW, policy(exam=True))  # 모레
    assert e.value.code == "OUT_OF_BOOKING_WINDOW"


def test_exam_mode_max_3_hours():
    with pytest.raises(BadRequestError) as e:
        validate_booking(at(20, 10), at(20, 14), NOW, policy(exam=True))
    assert e.value.code == "EXCEEDS_MAX_HOURS"
    assert "시험 기간" in e.value.message


def test_midnight_close_hour_24_supported():
    """close_hour=24(자정 종료) 정책: 23~24시 허용, 다음 날 1시까지는 거부 (이전엔 500 오류)"""
    p = policy()
    p.close_hour = 24
    validate_booking(at(20, 23), at(21, 0), NOW, p)
    with pytest.raises(BadRequestError) as e:
        validate_booking(at(20, 23), at(21, 1), NOW, p)
    assert e.value.code == "INVALID_TIME_RANGE"


def test_timezone_aware_input_rejected():
    """'+09:00'이 붙은 시각 → 400 (이전엔 naive/aware 비교로 500 오류)"""
    from datetime import timedelta, timezone

    kst = timezone(timedelta(hours=9))
    with pytest.raises(BadRequestError) as e:
        validate_booking(
            at(20, 10).replace(tzinfo=kst), at(20, 12).replace(tzinfo=kst), NOW, policy()
        )
    assert e.value.code == "INVALID_TIME_RANGE"


# ── 조회(US-04)·예약(US-05)이 같은 규칙인지 — 의도된 차이는 '진행 중 시간대'뿐 ──


def test_view_allows_in_progress_slot_but_booking_does_not():
    """10:15에 10~11시: 조회는 가능('사용 중' 확인), 예약은 불가(이미 시작)"""
    now = at(20, 10, 15)
    validate_view(at(20, 10), at(20, 11), now, policy())
    with pytest.raises(BadRequestError) as e:
        validate_booking(at(20, 10), at(20, 11), now, policy())
    assert e.value.code == "OUT_OF_BOOKING_WINDOW"


def test_view_rejects_finished_slot():
    with pytest.raises(BadRequestError) as e:
        validate_view(at(20, 10), at(20, 11), at(20, 11), policy())
    assert e.value.code == "OUT_OF_BOOKING_WINDOW"


def test_view_does_not_limit_hours():
    """조회는 넓은 구간(09~22시)도 허용, 예약만 최대 시간 적용"""
    validate_view(at(20, 9), at(20, 22), NOW, policy())


@pytest.mark.parametrize("fn", [validate_view, validate_booking], ids=["조회", "예약"])
@pytest.mark.parametrize("slot_minutes", [0, -60, 840], ids=["0분", "음수", "운영시간초과"])
def test_broken_policy_is_503_for_both(fn, slot_minutes):
    """정책 값이 잘못되면 조회·예약 모두 503 (예전 예약은 0으로 나누기 오류로 500)"""
    p = policy()
    p.slot_minutes = slot_minutes
    with pytest.raises(ServiceUnavailableError) as e:
        fn(at(20, 10), at(20, 11), NOW, p)
    assert e.value.code == "OPERATION_POLICY_UNAVAILABLE"
