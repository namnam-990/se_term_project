"""시험 기간 모드 전환 — 데모용 (FR-R-03 표시 확인). 관리자 화면(US-15)은 Sprint 2.

python -m scripts.exam_mode on     # 시험 기간: 당일~다음 날, 최대 3시간
python -m scripts.exam_mode off    # 평상시: 오늘~+7일, 최대 4시간
"""

import sys

from app.core.database import SessionLocal
from app.repositories.policy_repository import get_current_policy

if __name__ == "__main__":
    if len(sys.argv) != 2 or sys.argv[1] not in ("on", "off"):
        sys.exit("usage: python -m scripts.exam_mode on|off")
    with SessionLocal() as db:
        policy = get_current_policy(db)
        policy.exam_mode = sys.argv[1] == "on"
        db.commit()
        print(f"exam_mode={policy.exam_mode}", end=" ")
        print(f"days_ahead={policy.days_ahead} max_hours={policy.max_hours}")
