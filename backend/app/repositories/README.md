# repositories

SQLAlchemy 조회·저장·잠금만 담당합니다. 업무 판단(if 정책…)은 Service에 둡니다.

파일 예시 (담당자가 생성):
- `user_repository.py` — `find_by_login_id`, `lock_by_id` (`with_for_update()`)
- `seat_repository.py` — `list_enabled`, `lock_by_id`
- `reservation_repository.py` — `find_overlapping_by_seat`, `find_overlapping_by_user`, `find_by_request_key`, `list_by_user`
- `restriction_repository.py` — `find_active(user_id, now)`

겹침 조건(설계서): `Reservation.start_at < :end_at AND Reservation.end_at > :start_at AND status IN (RESERVED, CHECKED_IN)`
