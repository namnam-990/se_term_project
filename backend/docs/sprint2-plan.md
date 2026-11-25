# Sprint 2 계획 — Quality & Admin (운영 가능 상태)

| 항목 | 내용 |
|---|---|
| 기간 | 2026-__-__ ~ 2026-__-__ (최종 데모: __/__) |
| 목표 | 예약 → **15분 내 QR 체크인 → 사용 중 → 퇴실**, 미체크인 → **자동 취소 → 노쇼 3회 → 3일 제한**, 관리자 대시보드·정책 전환이 실제로 동작 |
| 총 SP | **37 SP (Must 33)** — Backlog v1.2.0 (US-19 퇴실 추가, `decisions.md` 0장 예외) |
| 기준 문서 | 명세서 최우선, 미정·불일치는 [`decisions.md`](decisions.md) 5장(D-29~D-51)·6장(설계서 대비 기록) |

## 1. 담당 배정 (⚠️ 제안안 — Sprint Planning에서 확정 후 수정)

Sprint 1처럼 **기능 단위**로 나누고, 각자 Sprint 1 코드와 이어지게 했습니다.

| 담당 | User Story | SP | 주 작업 파일 |
|---|---|---|---|
| 조성민 | US-08 체크인 · US-10 노쇼 자동 처리 · US-19 퇴실 · 동시성 통합 테스트 | 15 | `services/checkin_service.py`, `services/no_show_service.py`(run·apply), `core/scheduler.py`, `reservation_service.checkout`, `templates/checkin/kiosk.html`, `static/js/kiosk.js`, `tests/integration/test_us08_us10_race.py` |
| 김현진 | US-07 QR 발급 · US-12 대시보드 · US-15 정책 전환 · (Could) US-16 통계 | 10 + 2 | `services/qr_service.py`, `AdminDashboardService`·`StatisticsService`(`services/admin_service.py`), `policy_service.update`, `templates/admin/dashboard·policy·statistics.html`, `templates/reservations/my.html`(QR·퇴실 버튼) |
| 남준혁 | US-11 강제 취소 · US-13 학생 검색 · US-14 제한·초기화 · (Could) US-17 권한 | 8 + 2 | `AdminReservationService`·`AdminUserService`(`services/admin_service.py`), `services/restriction_service.py`, `no_show_service.reset`, `templates/admin/users.html`, `static/js/admin-users.js` |

**공유 부품** — 먼저 만드는 사람과 쓰는 사람이 정해져 있습니다.

| 부품 | 만드는 사람 | 쓰는 곳 | 상태 |
|---|---|---|---|
| QR 문자열·토큰 (`qr_service.build_payload / parse_payload / qr_token`) | 미리 구현됨 | US-07 발급, US-08 체크인, `kiosk.js` | ✅ 구현·테스트 완료 (바꾸려면 두 담당자 합의) |
| `NoShowService.apply_penalty()` (노쇼 +1, 이벤트, 3회 이상 제한) | 조성민 | US-10, US-11 | 스켈레톤 |
| `RestrictionService` (자동 제한·수동 설정·해제) | 남준혁 | US-10, US-14 | 스켈레톤 |
| `AdminUserService.to_item()` (학생 응답 변환) | 남준혁 | US-13·14·17 | 스켈레톤 |

**공용 파일**(`app/core/*`, `app/models/*`, `app/schemas/*`, `static/js/api.js`, `base.html`, `style.css`, `requirements.txt`)을 바꾸는 PR은 **팀 전원**을 리뷰어로 지정합니다. 다른 사람 담당 파일을 고쳐야 하면 **먼저 알리고** PR 설명에 적습니다 (Sprint 1 회고).

## 2. 작업 순서와 의존 관계

```
Day 1  [전원] 이 문서·decisions.md 5장 확인 (☐ 항목 D-43·D-51 확정), pip install -r requirements.txt
         │
Day 2~ US-07 QR 발급 ──> US-08 체크인 ──> US-10 노쇼 자동 처리 ──> 통합 테스트(체크인 vs 자동 취소)
       RestrictionService ───────────────┘          │
       US-11 강제 취소 ←── NoShowService.apply_penalty
       US-13 학생 검색 ──> US-14 제한·초기화 · US-17(Could)
       US-12 대시보드 · US-15 정책 전환 · US-16(Could)     (병렬)
       US-19 퇴실 (US-08 이후)
마감-3일 Could (US-16·17)는 Must가 끝난 뒤에만
마감-2일 통합 리허설 (4장)
마감-1일 스프린트 로그②, 데모 문서
```

> 체크인(US-08)이 있어야 "체크인 안 함"을 판정할 수 있어서 US-10보다 먼저입니다.
> 단, US-10 단위 테스트는 `make_reservation(status=...)`로 데이터를 직접 만들기 때문에 US-08 완성 전에도 개발할 수 있습니다.

## 3. 스켈레톤 사용법

Sprint 1과 같은 방식입니다.

- **API·화면·서비스 틀이 이미 등록**돼 있고, 구현 전에는 `501 NOT_IMPLEMENTED`를 반환합니다.
- 각 서비스 메서드의 docstring에 **처리 순서와 결정 번호(D-xx)**를 적어 두었습니다. 그대로 따라 구현하세요.
- **AC 테스트가 미리 작성**돼 있고 `@pending`으로 건너뜁니다 (`tests/unit/test_us07_qr.py` ~ `test_us19_checkout.py`). 구현하면서 `@pending`을 지우고 통과시키세요.
- 권한 검사·라우팅은 이미 동작합니다 (예: 학생이 관리자 API 호출 → 403, `@pending` 없는 테스트로 확인).
- 노쇼 스케줄러는 `SCHEDULER_ENABLED=false`(기본)로 꺼져 있습니다. US-10 구현 후 `.env`와 `config.py` 기본값을 `true`로 바꿉니다. 테스트는 항상 끄고 `NoShowService(db, clock).run()`을 직접 호출합니다.
- 새 의존성: `APScheduler`(US-10), `segno`(US-07 QR 이미지). QR 읽기용 `jsQR`은 US-08 담당이 `app/static/vendor/jsQR.js`로 추가합니다 (MIT, 오프라인 데모를 위해 CDN 대신 파일로).

| US | 서비스 | 라우터 | 화면 | 테스트 |
|---|---|---|---|---|
| 07 | `qr_service.QrService.get_qr` | `routers/checkin.py` | `reservations/my.html` (QR 보기 버튼 추가) | `test_us07_qr.py` |
| 08 | `checkin_service.CheckInService.check_in` | `routers/checkin.py` | `checkin/kiosk.html`, `kiosk.js` | `test_us08_checkin.py` |
| 10 | `no_show_service.NoShowService.run·_auto_cancel·apply_penalty`, `restriction_service.apply_no_show_restriction` | (내부) `core/scheduler.py` | - | `test_us10_no_show.py` |
| 11 | `admin_service.AdminReservationService.cancel` | `routers/admin.py` | `admin/users.html` | `test_us11_admin_cancel.py` |
| 12 | `admin_service.AdminDashboardService.dashboard` | `routers/admin.py` | `admin/dashboard.html` | `test_us12_dashboard.py` |
| 13 | `admin_service.AdminUserService.list_users·to_item` | `routers/admin.py` | `admin/users.html` | `test_us13_users.py` |
| 14 | `restriction_service.set_manual·release`, `no_show_service.reset` | `routers/admin.py` | `admin/users.html` | `test_us14_restriction.py` |
| 15 | `policy_service.PolicyService.update` | `routers/admin.py` | `admin/policy.html` | `test_us15_policy_update.py` |
| 16 | `admin_service.StatisticsService.statistics` | `routers/admin.py` | `admin/statistics.html` | `test_us16_statistics.py` |
| 17 | `admin_service.AdminUserService.change_role` | `routers/admin.py` | `admin/users.html` | `test_us17_role.py` |
| 19 | `reservation_service.ReservationService.checkout` | `routers/reservations.py` | `reservations/my.html` (퇴실 버튼 추가) | `test_us19_checkout.py` |

## 4. AC 체크리스트 (Backlog v1.2.0 기준)

### US-07 QR 발급 (Must / 2) — 담당: ____
- [ ] AC1 RESERVED 예약에서 좌석 정보가 담긴 QR 표시 (D-29)
- [ ] AC2 취소·자동 취소 예약은 QR 비활성 + 사용 불가 안내 (D-33)
- [ ] AC3 타인 예약 QR 요청 → 403, 코드 노출 없음

### US-08 체크인 (Must / 5) — 담당: ____
- [ ] AC1 RESERVED + 시작 후 15분 이내 + 유효 QR → CHECKED_IN, 좌석 '사용 중' (D-30·32)
- [ ] AC2 잘못된 코드 / 이미 체크인된 예약 → 거부 + 안내
- [ ] AC3 시작 전 / 15분 경과 → 거부 + "체크인 가능 시간 아님" 안내
- [ ] (설계서) 체크인 vs 자동 취소 동시 발생 → 하나만 확정 (MySQL 통합 테스트)

### US-10 노쇼 자동 처리 (Must / 8) — 담당: ____
- [ ] AC1 15분 미체크인 → 10분 주기 작업이 AUTO_CANCELLED, 좌석 가용, 노쇼 +1 (D-34·37)
- [ ] AC2 노쇼 3회 이상 → 즉시 3일 이용 제한 (D-17 개정: 3회째부터 노쇼마다)
- [ ] AC3 3일 경과 → 자동 해제 (카운터는 유지)
- [ ] AC4 기준 시각을 15분·3일 경계로 조작해도 정확히 동작 (FixedClock)
- [ ] (설계서) 재실행해도 이중 집계 없음, 실패 시 롤백 후 다음 실행에서 재검사

### US-11 강제 취소 (Must / 3) — 담당: ____
- [ ] AC1 사유 + 패널티 미부여 → 취소, 사유 기록, 좌석 즉시 가용 (D-39·40)
- [ ] AC2 사유 + 패널티 부여 → 취소 + 노쇼 +1 (D-41)
- [ ] AC3 사유 없음 → 거부 + 사유 필수 안내

### US-12 대시보드 (Must / 3) — 담당: ____
- [ ] AC1 이용 인원·잔여 좌석·가동률 (D-42, 설계서 5장 식)
- [ ] AC2 축소 그리드 **3상태**: 빈 좌석·사용 중·체크인 대기
- [ ] AC3 예약·체크인·취소 후 갱신하면 지표와 그리드 일치

### US-13 학생 검색 (Must / 2) — 담당: ____
- [ ] AC1 전체 목록 (학번·이메일·계정 상태·노쇼 횟수·제한 여부)
- [ ] AC2 학번 / 좌석번호 검색 (D-43)
- [ ] AC3 결과 없음 → 오류 없이 안내

### US-14 제한·초기화 (Must / 3, FR-A-12는 명세 '권장' → D-24) — 담당: ____
- [ ] AC1 제한 일자 지정 → 즉시 제한, 그날이 끝날 때까지 예약 차단 (D-51)
- [ ] AC2 해제 → 즉시 예약 가능
- [ ] AC3 노쇼 초기화 → 횟수 0, 이력은 `reset_at`으로 보존 (진행 중 제한은 유지)

### US-15 정책 전환 (Must / 5) — 담당: ____
- [ ] AC1 시험 기간 활성 → 최대 3시간 명시, 당일~다음 날·3시간 제한 (표시·검증은 Sprint 1 완료 → **관리자 전환 기능**)
- [ ] AC2 평상시로 전환 → 코드 변경 없이 +7일·4시간
- [ ] AC3 시험 기간에 3시간 초과·다음 날 이후 → 거부 + 안내 (Sprint 1 완료, 회귀 확인)
- [ ] (D-45) 잘못된 값 400, 기존 예약 유지

### US-19 퇴실 (Must / 2) — 담당: ____
- [ ] AC1 본인 CHECKED_IN → COMPLETED, 퇴실 시각 기록, 좌석 즉시 '예약 가능'
- [ ] AC2 체크인 전·취소·자동 취소·이용 완료 → 거부 + 안내
- [ ] AC3 타인 예약 → 403
- [ ] AC4 노쇼 횟수 불변

### Could — 시간이 남을 때만
- [ ] US-16 AC1 기간별 가동률 / AC2 시작 > 종료 → 오류 / AC3 데이터 없음 → 0%
- [ ] US-17 AC1 부여 / AC2 회수 / AC3 본인 회수 거부

## 5. 최종 데모 시나리오 (리허설용, 초안)

1. 학생 로그인 → 좌석 예약 → 내 예약에서 **QR 보기**
2. 서버 PC `localhost/kiosk`(관리자 로그인)에서 학생 기기의 QR을 웹캠으로 스캔 → **체크인 완료** → 좌석 화면 '사용 중'
3. 같은 QR 다시 → "이미 체크인" / 시작 전 예약 QR → "체크인 가능 시간 아님"
4. 학생 **퇴실** → 좌석 '예약 가능'
5. 미체크인 예약 → 자동 취소(노쇼) → 노쇼 3회 학생 예약 시도 → "이용 제한 중, 해제일" (스케줄러 대기 대신 테스트 실행 화면 또는 시각 조작으로 제시)
6. 관리자 대시보드 지표·3상태 그리드 → 학생 검색 → **강제 취소**(사유·패널티) → 제한 해제·노쇼 초기화
7. 관리자 정책 화면에서 **시험 기간 전환** → 학생 화면에 3시간 표시, 4시간 예약 거부
8. 동시성: 체크인 vs 자동 취소 통합 테스트 실행 화면
9. 팀원별 코드 설명 + Backlog·설계서와 달라진 점 (`decisions.md` 5·6장)

> 체크인 시연 준비물: 웹캠 있는 서버 PC + 학생 QR을 띄울 기기. 학교 Wi-Fi에서 기기끼리 접속이 막히면 휴대폰 핫스팟 또는 미리 찍어 둔 QR 사진 (토큰은 예약마다 고정, D-29).

## 6. Sprint 1 회고에서 가져온 규칙
- 다른 사람 파일을 고칠 땐 먼저 알리고 PR에 적기
- PR 머지 전 리뷰어가 `pytest` 결과를 코멘트로 남기기 (CI 없음)
- 커밋 전에 `git branch`로 현재 브랜치 확인
- 화면은 실제로 써 보면서 확인 (분 단위 입력 불편을 써 보고 발견한 경험)
