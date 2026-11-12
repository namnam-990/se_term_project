"""시간 추상화 — 요구사항 4.2 '스케줄러·체크인 로직은 시간 조작이 가능하도록 설계'.

코드 어디에서도 datetime.now()를 직접 부르지 말고 Clock을 주입받아 사용한다.
테스트에서는 FixedClock으로 바꿔 끼워 15분·3일 경계를 검증한다.
DB에는 KST naive datetime으로 저장한다(MySQL 서버 타임존 +09:00).
"""

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

KST = ZoneInfo("Asia/Seoul")


class Clock:
    def now(self) -> datetime:
        return datetime.now(KST).replace(tzinfo=None, microsecond=0)


class FixedClock(Clock):
    """테스트용: 고정 시각, advance()로 시간 이동."""

    def __init__(self, fixed: datetime):
        self._now = fixed

    def now(self) -> datetime:
        return self._now

    def advance(self, **kwargs) -> None:
        self._now += timedelta(**kwargs)


_clock: Clock = Clock()


def get_clock() -> Clock:
    """FastAPI 의존성. 테스트에서는 app.dependency_overrides[get_clock] 으로 교체."""
    return _clock
