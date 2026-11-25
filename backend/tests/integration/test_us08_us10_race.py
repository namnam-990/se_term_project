"""US-08 × US-10 — 체크인과 노쇼 자동 취소가 동시에 일어나도 하나만 확정 (MySQL 필요, Sprint
2 스켈레톤).

설계서 Core Flow 3: "체크인과 경합 시 하나만 확정하고, 실패 시 전체 롤백·다음 실행 재검사한다."
설계서 5장 테스트: "MySQL 별도 연결로 … 체크인·자동 취소 경합, 재실행·롤백 … 을 검증한다."

시나리오 (US-08·US-10 구현 후 담당자가 작성)
- 마감 직전(예: 10:14:59) 체크인 요청과 run()을 별도 세션·스레드로 동시에 실행
  → 최종 상태는 CHECKED_IN 또는 AUTO_CANCELLED 중 **하나**, NoShowEvent는 0건 또는 1건
- run()을 두 세션에서 동시에 실행 → 노쇼 카운터는 1만 증가 (회원·예약 잠금 + UNIQUE)
참고: tests/integration/test_us05_concurrency.py 의 엔진·스레드 구성
"""

import pytest

pytestmark = pytest.mark.integration
pending = pytest.mark.skip(reason="US-08·US-10 구현 후 작성 — Sprint 2 스켈레톤")


@pending
def test_check_in_vs_auto_cancel_only_one_wins(mysql_url):
    raise NotImplementedError


@pending
def test_concurrent_no_show_runs_count_once(mysql_url):
    raise NotImplementedError
