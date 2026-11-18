"""개발용 로그인 — US-02(로그인) 구현 전에 화면을 확인하기 위한 임시 도구. 데모에서는 쓰지 않는다.

    python -m scripts.dev_login 202200001

시드 계정으로 세션(AuthSession)을 만들고, 브라우저 개발자 도구(F12) → Console에
붙여 넣을 쿠키 설정 코드를 출력한다.
  - access_token : 인증 (core/deps.get_current_user가 쿠키에서 읽음)
  - csrf_token   : POST 요청 검증 (core/csrf.verify_csrf, api.js가 헤더로 복사)
"""

import sys
from datetime import timedelta

from sqlalchemy import select

from app.core.clock import Clock
from app.core.database import SessionLocal
from app.core.security import create_access_token, new_token, sha256
from app.models import AccountStatus, AuthSession, User

if __name__ == "__main__":
    login_id = sys.argv[1] if len(sys.argv) > 1 else "202200001"
    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.login_id == login_id))
        if user is None:
            sys.exit(f"'{login_id}' 계정이 없습니다. 먼저 python -m scripts.seed 를 실행하세요.")
        if user.account_status != AccountStatus.ACTIVE:
            print(f"⚠️ {login_id} 계정 상태가 {user.account_status.value}라 API가 403을 돌려줍니다.")
        session = AuthSession(
            user_id=user.id,
            refresh_token_hash=sha256(new_token()),
            expires_at=Clock().now() + timedelta(days=1),
        )
        db.add(session)
        db.commit()
        token = create_access_token(user.id, user.role.value, session.id)

    csrf = new_token(16)
    print(f"\n[{login_id}] 개발용 로그인 (토큰 유효 1시간)")
    print("브라우저에서 http://127.0.0.1:8000 을 연 뒤")
    print("F12 → Console 에 아래 두 줄을 붙여 넣고 새로고침:\n")
    print(f'document.cookie = "access_token={token}; path=/";')
    print(f'document.cookie = "csrf_token={csrf}; path=/";\n')
