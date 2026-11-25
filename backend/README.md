# LSRS — 도서관 좌석 예약 시스템 (5조)

> Library Seat Reservation System · Python 3.11 · FastAPI · Jinja2 · SQLAlchemy · MySQL 8.0

| 역할 | 이름 | 학번 |
|---|---|---|
| Product Owner | 김현진 | 202202579 |
| Scrum Master | 남준혁 | 202201693 |
| Developer | 조성민 | 202202644 |

## 1. 현재 스프린트

**Sprint 2 — Quality & Admin (37 SP)**: QR 체크인·퇴실, 노쇼 자동 취소·이용 제한, 관리자 대시보드·학생 관리·정책 전환
→ 계획·담당·AC 체크리스트·스켈레톤 사용법: [`docs/sprint2-plan.md`](docs/sprint2-plan.md)
→ 결정 기록 (D-29~D-51, 설계서 대비 기록): [`docs/decisions.md`](docs/decisions.md) 5·6장

**개발 상태**: Sprint 1(US-01~06·09) 구현 완료. Sprint 2는 **스켈레톤 단계** — API·화면·서비스 틀이 등록돼 있고 구현 전에는 `501 NOT_IMPLEMENTED`를 반환합니다. AC 테스트는 `@pending`으로 건너뜁니다.

<details><summary>Sprint 1 — Core (30 SP)</summary>

회원 인증, 실시간 좌석 조회, 동시성 안전 예약, 내역 조회, 직접 취소
→ [`docs/sprint1-plan.md`](docs/sprint1-plan.md) · 데모 [`docs/sprint1-demo.md`](docs/sprint1-demo.md) · 코드 설명 [`docs/code-notes/`](docs/code-notes/)
</details>

## 2. 빠른 시작

> ⚠️ 서버·테스트·스크립트는 **항상 `backend` 폴더 안에서** 실행합니다. 레포 루트에서 실행하면 `Directory 'app/static' does not exist` 오류가 납니다.
>
> 필요한 것: Python 3.11 이상(3.12 동작 확인), Git, Docker Desktop(MySQL용)

### 2.1 처음 한 번 — 설치

**Windows (PowerShell)**

```powershell
git clone <repo-url> se_term_project
cd se_term_project
git switch main; git pull
cd backend

python -m venv .venv
.\.venv\Scripts\Activate.ps1          # 프롬프트 앞에 (.venv)가 보여야 함
pip install -r requirements-dev.txt
Copy-Item .env.example .env            # 값은 각자 로컬에 맞게 (커밋 금지)
```

> `Activate.ps1` 실행이 막히면 한 번만: `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`

**macOS / Linux**

```bash
git clone <repo-url> se_term_project && cd se_term_project/backend
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env
```

### 2.2 DB 준비 — MySQL + 테이블 + 시드

Docker Desktop을 먼저 실행해 두세요 (엔진이 꺼져 있으면 `docker compose`가 실패합니다).

```powershell
docker compose up -d db                     # MySQL 8.0 (서비스 이름: db)
python -m scripts.init_db                   # 테이블 생성 (--reset: 전부 지우고 다시 생성)
python -m scripts.seed --reset-policy       # 좌석 40석 + 계정 5개 + 운영 정책 06~23시·30분
```

- `--reset-policy`는 DB에 이미 들어 있는 운영 정책을 기본값(06~23시·30분 단위)으로 되돌립니다. 정책 기본값이 바뀐 뒤에는 꼭 다시 실행하세요.
- Docker 없이 로컬 MySQL을 쓰면 `lsrs` DB와 계정을 만든 뒤 `.env`의 `DATABASE_URL`만 맞추면 됩니다.

### 2.3 서버 실행

```powershell
uvicorn app.main:app --reload
```

- 화면: http://127.0.0.1:8000 · Swagger API 문서: http://127.0.0.1:8000/docs
- 다음에 다시 실행할 때는 `cd backend` → venv 활성화 → `docker compose up -d db` → `uvicorn ...`만 하면 됩니다.

### 2.4 테스트 계정 (`scripts/seed.py`)

| 로그인 ID | 상태 | 비밀번호 | 용도 |
|---|---|---|---|
| `admin` | 관리자 | `Admin!2345` | 관리자 권한 |
| `202200001` | 학생 ACTIVE | `Student!234` | 기본 시연 계정 |
| `202200002` | 학생 ACTIVE | `Student!234` | 같은 좌석 충돌, 타인 예약 접근 |
| `202200003` | 학생 PENDING | `Student!234` | 이메일 미인증 로그인 차단 |
| `202200004` | 학생 + 이용 제한 3일 | `Student!234` | 제한 학생 예약 거부 |

### 2.5 회원가입·이메일 인증 (로컬)

`.env`의 `MAIL_BACKEND=console`(기본값)이면 **실제 메일을 보내지 않고, uvicorn을 실행한 터미널에 메일 내용이 출력**됩니다.

1. `/signup`에서 가입 신청 (`ALLOWED_EMAIL_DOMAIN`이 비어 있으면 아무 이메일이나 가능)
2. 서버 터미널에서 아래 출력 확인
   ```
   ===== [MAIL to test@example.com] LSRS 이메일 인증 =====
   인증 코드: 482913
   인증 링크: http://127.0.0.1:8000/verify-email?token=...
   ```
3. `/verify-email`에서 이메일 + 6자리 코드 입력, 또는 인증 링크를 브라우저 주소창에 붙여 넣기
4. `/login`에서 학번·비밀번호로 로그인 → 학생은 `/seats`로 이동

- 인증 정보는 **10분** 동안 유효하고 재발송 기능은 없습니다. 만료되면 다른 학번·이메일로 다시 가입하세요.
- 실제 메일 발송은 `MAIL_BACKEND=smtp`와 `SMTP_*` 값을 설정합니다 (Gmail은 앱 비밀번호 필요). 비밀번호가 든 `.env`는 절대 커밋하지 않습니다.

### 2.6 개발·데모 보조 스크립트

```powershell
python -m scripts.exam_mode on|off          # 시험 기간 정책 켜기/끄기 (당일~다음 날, 최대 3시간)
docker compose exec db mysql -ulsrs -plsrs_pw lsrs -e "select student_no,account_status,role from users;"
```

## 3. 테스트·린트

```powershell
pytest                     # 전체 (MySQL 통합 테스트는 TEST_DATABASE_URL 없으면 skip)
pytest tests/unit          # DB 없이 빠르게
pytest tests/unit/test_us01_signup.py -v    # 특정 파일만
ruff check . ; ruff format --check .
```

**MySQL 통합 테스트(동시성)**: `docker compose up -d db`가 만든 `lsrs_test` DB를 사용합니다.

```powershell
$env:TEST_DATABASE_URL="mysql+pymysql://lsrs:lsrs_pw@127.0.0.1:3306/lsrs_test?charset=utf8mb4"
pytest tests/integration -v
```

- macOS/Linux: `export TEST_DATABASE_URL=...`
- `lsrs_test` DB가 없다는 오류가 나면 MySQL 볼륨이 예전에 만들어진 경우입니다: `docker compose down -v` → `docker compose up -d db` → `init_db`·`seed` 다시 실행 (로컬 데이터 삭제됨)
- skip된 통합 테스트는 통과로 계산하지 않습니다.

**CI는 없습니다.** PR을 머지하기 전에 리뷰어가 해당 브랜치를 받아 `pytest`를 직접 실행하고 결과를 PR 코멘트로 남깁니다.

### 자주 나는 오류

| 증상 | 원인 → 해결 |
|---|---|
| `Directory 'app/static' does not exist` | 레포 루트에서 실행함 → `cd backend` |
| `No module named 'sqlalchemy'` 등 | venv 미활성화 → `.\.venv\Scripts\Activate.ps1` |
| `ZoneInfoNotFoundError: Asia/Seoul` (Windows) | `pip install -r requirements.txt`로 `tzdata` 설치 |
| `Can't connect to MySQL` / connection refused | Docker Desktop 실행 → `docker compose up -d db` 후 몇 초 대기 |
| 좌석 화면 시간이 예전(9~22시, 1시간) 그대로 | `python -m scripts.seed --reset-policy` |
| 가입했는데 인증 메일이 안 옴 | 정상 — 서버 터미널에 출력됨 (2.5) |

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
scripts/                 # init_db, seed, exam_mode, dev_login(US-02 이전 임시 도구)
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
- [`docs/decisions.md`](docs/decisions.md) — **설계 구체화·보완 기록** (문서 불일치 정리, 발표용 요약)
- [`docs/api-contract.md`](docs/api-contract.md) — Sprint 1 API 계약·오류 코드
- [`docs/sprint-log/sprint1-log.md`](docs/sprint-log/sprint1-log.md) — 스프린트 로그① (AI 활용 기록)
