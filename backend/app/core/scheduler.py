"""노쇼 감지 스케줄러 — US-10 (설계서 5장: APScheduler 단일 인스턴스, 명세서 4.4: 10분 주기).

담당: US-10 담당자 (sprint2-plan.md)

설계 원칙 (D-37)
- 스케줄러는 '언제 실행할지'만 담당하고, 업무 로직은 전부 NoShowService.run()에 둔다.
  → 테스트는 스케줄러 없이 FixedClock으로 run()을 직접 호출해 15분·3일 경계를 검증한다 (명세서 4.2).
- 실행할 때마다 새 DB 세션을 연다 (요청 세션과 공유하지 않음).
- 서버가 여러 개 떠도 이중 처리되지 않도록 NoShowService가 회원·예약 잠금 +
  NoShowEvent.reservation_id UNIQUE로 막는다 (설계서 Core Flow 3).
- 주기(scheduler_minutes)는 서버 시작 시 정책 값을 읽는다. 바꾸면 재시작 후 반영 (D-45).

설정 `SCHEDULER_ENABLED=false`(기본)이면 시작하지 않는다. US-10 구현 후 기본값을 True로 바꾼다.
"""

import logging

from app.core.clock import Clock
from app.core.database import SessionLocal

log = logging.getLogger("lsrs.scheduler")


def run_no_show_job() -> None:
    """스케줄러가 주기마다 호출. 예외가 나도 스케줄러가 멈추지 않도록 로그만 남긴다."""
    from app.services.no_show_service import NoShowService

    with SessionLocal() as db:
        try:
            processed = NoShowService(db, Clock()).run()
            if processed:
                log.info("no-show job: %d건 처리", processed)
        except Exception:  # noqa: BLE001 — 다음 실행에서 다시 검사 (설계서 Core Flow 3)
            log.exception("no-show job 실패 — 다음 실행에서 다시 검사합니다")


def start_scheduler():
    """앱 시작 시 호출 (main.py lifespan). 반환한 스케줄러는 종료 시 shutdown()."""
    # APScheduler는 Sprint 2에 추가한 의존성이라, 꺼져 있을 때는 import하지 않는다.
    from apscheduler.schedulers.background import BackgroundScheduler

    from app.repositories.policy_repository import read_current_policy

    with SessionLocal() as db:
        policy = read_current_policy(db)
        minutes = policy.scheduler_minutes if policy else 10

    scheduler = BackgroundScheduler(timezone="Asia/Seoul")
    # max_instances=1: 이전 실행이 안 끝났으면 겹쳐 실행하지 않음
    scheduler.add_job(run_no_show_job, "interval", minutes=minutes, id="no_show", max_instances=1)
    scheduler.start()
    log.info("no-show scheduler started (every %d min)", minutes)
    return scheduler
