import pytest
from sqlalchemy import create_engine, text

pytestmark = pytest.mark.integration


def test_mysql_reachable(mysql_url):
    engine = create_engine(mysql_url)
    with engine.connect() as conn:
        assert conn.execute(text("SELECT 1")).scalar() == 1


# TODO(US-05): 동시 예약 통합 테스트
# - init: Base.metadata.create_all(engine), 좌석 1개·학생 N명 생성
# - ThreadPoolExecutor로 N개 세션이 같은 좌석·시간 예약 동시 요청
# - 기대: 성공 1건, 나머지 ConflictError(409), DB의 겹치는 RESERVED 행 1개
