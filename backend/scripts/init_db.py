"""테이블 생성 (Sprint 1용). 스키마 변경 시: 팀 공지 → 각자 drop 후 재실행.

python -m scripts.init_db          # 없는 테이블만 생성
python -m scripts.init_db --reset  # 전체 삭제 후 재생성 (로컬 데이터 소실 주의)
"""

import sys

import app.models  # noqa: F401  (메타데이터 등록)
from app.core.database import Base, engine

if __name__ == "__main__":
    if "--reset" in sys.argv:
        Base.metadata.drop_all(engine)
        print("dropped all tables")
    Base.metadata.create_all(engine)
    print("tables:", ", ".join(Base.metadata.tables))
