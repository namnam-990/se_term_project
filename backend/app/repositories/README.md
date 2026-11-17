# repositories

SQLAlchemy 조회·저장·잠금만 담당합니다. 업무 판단(if 정책…)은 Service에 둡니다.

| 파일 | 사용하는 US |
|---|---|
| `user_repository.py` | US-01·02·03·05 |
| `seat_repository.py` | US-04·05 |
| `reservation_repository.py` | US-04·05·06·09 |
| `restriction_repository.py` | US-05 |
| `email_verification_repository.py` | US-01 |
| `auth_session_repository.py` | US-02 |
| `policy_repository.py` | US-04·05 |

- 잠금(`with_for_update`)은 MySQL에서만 실제로 동작합니다. SQLite 단위 테스트에서는 무시됩니다.
- 겹침 조건: `start_at < :end AND end_at > :start AND status IN (RESERVED, CHECKED_IN)` (경계 시각은 겹치지 않음)
