# LSRS — 도서관 좌석 예약 시스템 (5조)

> Library Seat Reservation System · Python 3.11 · FastAPI · Jinja2 · SQLAlchemy · MySQL 8.0

| 역할 | 이름 | 학번 |
|---|---|---|
| Product Owner | 김현진 | 202202579 |
| Scrum Master | 남준혁 | 202201693 |
| Developer | 조성민 | 202202644 |

## 1. 현재 스프린트

**Sprint 1 — Core (30 SP)**: 회원 인증, 실시간 좌석 조회, 동시성 안전 예약, 내역 조회, 직접 취소
→ 상세 계획·담당·AC 체크리스트: [`docs/sprint1-plan.md`](docs/sprint1-plan.md)

## 2. 빠른 시작

```bash
# 1) 저장소 클론 후 develop 브랜치로 이동
git clone <repo-url> lsrs && cd lsrs
git switch develop

# 2) 가상환경 + 의존성
python3.11 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt

# 3) 환경변수
cp .env.example .env               # 값은 각자 로컬에 맞게 수정 (커밋 금지)

# 4) MySQL 실행 (Docker 사용 시)
docker compose up -d db

# 5) 테이블 생성 + 시드 데이터(좌석 40석, 관리자 1명, 기본 정책)
python -m scripts.init_db
python -m scripts.seed

# 6) 서버 실행
uvicorn app.main:app --reload
# → http://127.0.0.1:8000        (화면)
# → http://127.0.0.1:8000/docs   (Swagger API 문서)
```

Docker 없이 로컬 MySQL을 쓰는 경우 `lsrs` DB와 계정을 만든 뒤 `.env`의 `DATABASE_URL`만 맞추면 됩니다.

## 3. 테스트·린트

```bash
pytest                     # 전체 (unit + integration)
pytest tests/unit          # DB 없이 빠르게
ruff check . && ruff format --check .
```

PR을 올리면 GitHub Actions(`.github/workflows/ci.yml`)가 동일한 검사를 자동으로 실행합니다.

## 4. 디렉터리 구조 (설계서 2장 계층 구조와 1:1 대응)

```
app/
├── main.py              # FastAPI 앱 생성, 라우터·예외 핸들러 등록
├── core/                # Common: 설정, DB 세션, 보안(JWT·BCrypt), Clock, 공통 예외
├── models/              # Domain: SQLAlchemy 엔티티 (설계서 3장 ERD)
├── schemas/             # Pydantic 요청/응답 DTO
├── routers/             # Router: Auth · Seat · Reservation (HTTP 입출력만)
├── services/            # Service: 업무 규칙과 트랜잭션 (핵심 로직은 여기에만)
├── repositories/        # Repository: 조회·저장·잠금(FOR UPDATE)
├── templates/           # View: Jinja2 화면
└── static/              # CSS / JS (fetch 래퍼)
scripts/                 # init_db, seed
tests/unit · integration # pytest
docs/                    # 스프린트 계획, API 계약, 스프린트 로그(AI 활용 기록)
```

**의존 방향 규칙**: `routers → services → repositories → models` (역방향 import 금지).
Router에서 DB를 직접 조회하거나, Service에서 `Request`/`Response`를 다루지 않습니다.

## 5. 협업 규칙

브랜치·커밋·PR·리뷰 규칙은 [`CONTRIBUTING.md`](CONTRIBUTING.md)를 반드시 읽고 시작하세요.

## 6. 참고 문서

- 문제정의서 / Product Backlog / 시스템 구조 설계서 (팀 공유 드라이브)
- 요구사항 명세서 v1.0 (주제 A)
- [`docs/api-contract.md`](docs/api-contract.md) — Sprint 1 API 계약·오류 코드
- [`docs/sprint-log/sprint1-log.md`](docs/sprint-log/sprint1-log.md) — 스프린트 로그① (AI 활용 기록)
