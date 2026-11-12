# 협업 가이드 (CONTRIBUTING)

## 1. 브랜치 전략 (간소화 Git Flow)

```
main      ← 데모/제출용. 스프린트 종료 시 develop에서만 병합 (직접 push 금지)
develop   ← 통합 브랜치. 기능 브랜치는 PR로만 병합
feature/US-05-reservation-create   ← 작업 브랜치 (US 번호 필수)
fix/US-05-overlap-check            ← 버그 수정
chore/ci-setup, docs/sprint1-log   ← 설정·문서
```

- 작업 시작: `git switch develop && git pull && git switch -c feature/US-XX-설명`
- 하루 1회 이상 `develop`을 rebase 또는 merge 해서 충돌을 작게 유지
- 병합 후 기능 브랜치는 삭제

**GitHub 설정(SM 담당, 1회)**: Settings → Branches → `main`, `develop`에 보호 규칙
(Require a pull request · Require 1 approval · Require status checks: `ci`).

## 2. 커밋 메시지

```
<type>(<scope>): <요약>          ← 50자 이내, 현재형

<본문: 무엇을/왜 (선택)>

Refs: #이슈번호
```

| type | 용도 |
|---|---|
| `feat` | 기능 추가 |
| `fix` | 버그 수정 |
| `test` | 테스트 추가·수정 |
| `refactor` | 동작 변화 없는 구조 개선 |
| `docs` | 문서 |
| `chore` | 빌드·설정·의존성 |

scope는 US 번호 또는 계층: `feat(US-05): 좌석 FOR UPDATE 잠금 후 겹침 재검사`

**AI 생성 코드를 커밋할 때**는 본문에 `AI: <도구명> 초안 → <직접 수정한 내용>`을 한 줄 남깁니다.
이 기록이 스프린트 로그의 "AI 오류 대응 사례" 근거가 됩니다.

## 3. Pull Request

1. 이슈(User Story/Task) 먼저 만들고 PR 본문에 `Closes #번호`
2. PR 템플릿의 AC 체크리스트를 모두 채움
3. **리뷰어 1명 이상 승인 + CI 통과** 후 *Squash and merge*
4. PR 크기: 변경 400줄 이하 권장 (넘으면 쪼개기)
5. 리뷰어는 24시간 이내 응답. 리뷰 시 "이 코드가 **왜** 이렇게 동작하는지" 질문하기
   → 중간 데모에서 각자 코드 설명이 필수(루브릭 8절)이므로 리뷰가 곧 데모 준비입니다.

## 4. 코드 규칙

- 포매터/린터: `ruff format`, `ruff check` (설정: `pyproject.toml`)
- 이름: 파일·함수·변수 `snake_case`, 클래스 `PascalCase`, 상수 `UPPER_SNAKE`
- **정책 값 하드코딩 금지** (요구사항 4.1): 예약 가능 일수·최대 시간·15분·3회·3일 등은
  `OperationPolicy`(DB)에서 읽습니다.
- **현재 시각은 `datetime.now()` 직접 호출 금지** → `app.core.clock.Clock` 주입 (테스트 시간 조작용, 요구사항 4.2)
- 오류는 `app.core.exceptions.AppError` 하위 예외를 raise → 공통 핸들러가 `{code, message}`로 변환
- SQL은 SQLAlchemy 바인딩만 사용 (문자열 포매팅 쿼리 금지)
- 비밀값(.env, 비밀번호, 토큰)은 절대 커밋하지 않음

## 5. 테스트 규칙

- 서비스 로직은 `tests/unit`에 단위 테스트 (Clock·Repository Mock)
- DB 잠금·동시성은 `tests/integration` (MySQL 필요, `@pytest.mark.integration`)
- AC 하나당 테스트 최소 1개. 테스트 이름에 US 번호: `test_us05_concurrent_reservation_only_one_succeeds`

## 6. 회의·기록

| 언제 | 무엇 | 기록 위치 |
|---|---|---|
| 스프린트 시작 | Sprint Planning (담당·SP 확정) | `docs/sprint1-plan.md` |
| 매일(또는 작업일) | 데일리 스크럼 3문항 | GitHub Discussions 또는 카톡 공지 → 주 1회 로그에 요약 |
| AI 사용 직후 | 프롬프트·오류·수정 내역 | `docs/sprint-log/sprint1-log.md` 개인 섹션 |
| 스프린트 종료 | 리뷰·회고 | 스프린트 로그 |
