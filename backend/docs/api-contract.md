# API 계약 — Sprint 1 · 2

설계서 4장(REST Endpoint Catalog). Sprint 2 항목은 스켈레톤(501)으로 등록돼 있고, 구현하면서 이 표를 기준으로 맞춘다. 명세서와 충돌하면 [`decisions.md`](decisions.md)를 따릅니다. 필드명은 `app/schemas/*.py`가 기준이며, 바꾸면 이 문서도 같은 PR에서 수정합니다.

## 공통

- 날짜·시간: ISO-8601, 한국 시간(KST) 기준 timezone 없는 값 — `2026-11-20T10:00:00`
- 인증: HttpOnly 쿠키 `access_token` (화면) 또는 `Authorization: Bearer <token>` (Swagger/테스트)
- CSRF (D-02): 쿠키로 인증하는 POST/PUT/DELETE는 `X-CSRF-Token` 헤더 = `csrf_token` 쿠키 값. `static/js/api.js`가 자동으로 붙임. Bearer 호출은 생략
- 오류 응답: `{"code": "...", "message": "사용자에게 보여줄 문장"}` (+필요 시 추가 필드)

| HTTP | 의미 |
|---|---|
| 200 / 201 | 성공 / 가입 생성 |
| 400 | 입력·정책 위반 |
| 401 | 미인증·토큰 만료·로그아웃된 세션 |
| 403 | 권한 없음·PENDING·LOCKED·이용 제한 |
| 404 | 대상 없음 |
| 409 | 충돌 (중복 가입, 좌석/시간 겹침, 취소 불가 상태) |
| 503 | 메일 발송 실패·운영 정책 이상 |
| 501 | 스켈레톤 미구현 (개발 중에만) |

## 엔드포인트

| Method | Path | 권한 | US | 요청 | 응답 |
|---|---|---|---|---|---|
| POST | `/api/auth/signup` | 공개 | 01 | `SignupRequest` | 201 `SignupResponse` |
| POST | `/api/auth/email-verifications` | 공개 | 01 | `EmailVerifyRequest` (`token` 또는 `email`+`code`, D-03) | `MessageResponse` |
| POST | `/api/auth/login` | 공개 | 02·03 | `LoginRequest` | `LoginResponse` + 쿠키 |
| POST | `/api/auth/refresh` | refresh 쿠키 보유 | 02 | - | `LoginResponse` + 쿠키 갱신 (D-05, CSRF 헤더 필요) |
| POST | `/api/auth/logout` | 로그인 | 02 | - | `MessageResponse` |
| GET | `/api/auth/me` | 로그인 | 02 | - | `MeResponse` |
| GET | `/api/policies/current` | 로그인 | 04 (FR-R-03) | - | `PolicyView` (구현 완료) |
| GET | `/api/seats?start_at=&end_at=` | 학생 | 04 | query | `SeatGridResponse` (+ `bookable`, `notice`: 그 구간을 그대로 예약할 수 있는지, D-28) |
| POST | `/api/reservations` | 학생 | 05 | `ReservationCreateRequest` | `ReservationResponse` |
| GET | `/api/me/reservations?status=` | 학생 | 06 | query | `ReservationListResponse` |
| POST | `/api/reservations/{id}/cancel` | 학생(본인) | 09 | `ReservationCancelRequest` | `ReservationResponse` |

### Sprint 2

| Method | Path | 권한 | US | 요청 | 응답 |
|---|---|---|---|---|---|
| GET | `/api/reservations/{id}/qr` | 학생(본인) | 07 | - | `QrResponse` (`active`=false면 `payload`·`svg` 없음, D-33) |
| POST | `/api/reservations/{id}/check-in` | **관리자(체크인 단말)** | 08 | `CheckInRequest {token}` | `ReservationResponse` (D-30) |
| POST | `/api/reservations/{id}/checkout` | 학생(본인) | 19 | - | `ReservationResponse` (COMPLETED) |
| POST | `/api/admin/reservations/{id}/cancel` | 관리자 | 11 | `AdminCancelRequest {reason, detail, apply_penalty}` | `ReservationResponse` |
| GET | `/api/admin/dashboard` | 관리자 | 12 | - | `DashboardResponse` (그리드 3상태 `EMPTY·IN_USE·WAITING`, D-42) |
| GET | `/api/admin/users?student_no=&seat_number=` | 관리자 | 13 | query | `AdminUserListResponse` (학생별 `reservations` 포함, D-38) |
| PUT | `/api/admin/users/{id}/restriction` | 관리자 | 14 | `RestrictionSetRequest {until, reason}` | `AdminUserItem` |
| DELETE | `/api/admin/users/{id}/restriction` | 관리자 | 14 | - | `AdminUserItem` |
| POST | `/api/admin/users/{id}/no-shows/reset` | 관리자 | 14 | - | `AdminUserItem` |
| PUT | `/api/admin/policies/current` | 관리자 | 15 | `PolicyUpdateRequest` | `PolicyView` (초기값은 `GET /api/policies/current`) |
| GET | `/api/admin/statistics?from=&to=` | 관리자 | 16 (Could) | query | `StatisticsResponse` |
| PUT | `/api/admin/users/{id}/role` | 관리자 | 17 (Could) | `RoleChangeRequest {role}` | `AdminUserItem` |
| (내부) | 노쇼 스케줄러 10분 주기 | - | 10 | - | `NoShowService.run()` (D-37) |

**QR 문자열 (D-29)**: `LSRS|r=<예약ID>|seat=<좌석번호>|t=<토큰>` — `app/services/qr_service.py`의 `build_payload`·`parse_payload`가 기준. 바꾸면 US-07·08 담당자가 함께 수정.

## 오류 코드 목록

새 코드를 추가하면 여기에 한 줄 추가하세요.

| code | HTTP | 상황 | US |
|---|---|---|---|
| `VALIDATION_ERROR` | 400 | Pydantic 입력 검증 실패 | 공통 |
| `AUTH_REQUIRED` | 401 | 토큰 없음 | 공통 |
| `TOKEN_INVALID` | 401 | 서명 오류·만료 | 공통 |
| `SESSION_REVOKED` | 401 | 로그아웃·만료된 세션 | 02 |
| `FORBIDDEN_ROLE` | 403 | 역할 불일치 | 02 |
| `ACCOUNT_PENDING` | 403 | 이메일 인증 전 | 01·02 |
| `ACCOUNT_LOCKED` | 403 | 6번째 연속 실패 시점 및 이후 모든 로그인 (1~5번째 실패는 401 `LOGIN_FAILED`) | 03 |
| `PASSWORD_POLICY` | 400 | 8자 미만 / 영문·숫자·특수문자 누락 / UTF-8 72바이트 초과 | 01 |
| `DUPLICATE_STUDENT_NO` | 409 | 학번 중복 | 01 |
| `DUPLICATE_EMAIL` | 409 | 이메일 중복 | 01 |
| `INVALID_VERIFICATION` | 400 | 인증 코드·링크 불일치·만료 (10분, D-15) | 01 |
| `EMAIL_DOMAIN` | 400 | 학교 이메일 도메인 아님 (`ALLOWED_EMAIL_DOMAIN` 설정 시) | 01 |
| `MAIL_DELIVERY_FAILED` | 503 | 메일 발송 실패. 가입 트랜잭션은 롤백하여 재시도 가능 | 01 |
| `LOGIN_FAILED` | 401 | ID/비밀번호 불일치 (어느 쪽이 틀렸는지 노출 금지) | 02 |
| `OUT_OF_BOOKING_WINDOW` | 400 | 과거 / 예약 가능 일수 초과 | 04·05 |
| `INVALID_TIME_RANGE` | 400 | start ≥ end, 운영시간 밖, 단위 불일치 | 04·05 |
| `EXCEEDS_MAX_HOURS` | 400 | 최대 이용 시간 초과 | 05 |
| `USER_RESTRICTED` | 403 | 이용 제한 중 (+`restricted_until`) | 05 |
| `USER_TIME_OVERLAP` | 409 | 같은 학생 같은 시간대 예약 존재 | 05 |
| `SEAT_ALREADY_RESERVED` | 409 | 좌석이 이미 선택됨 | 05 |
| `SEAT_NOT_FOUND` | 404 | 좌석 없음·비활성 | 05 |
| `RESERVATION_NOT_FOUND` | 404 | 예약 없음 | 09 |
| `NOT_OWNER` | 403 | 타인 예약 | 09 |
| `NOT_CANCELLABLE` | 409 | RESERVED가 아닌 예약, 또는 체크인 마감(시작+15분) 이후 취소 (D-26) | 09 |
| `REQUEST_KEY_CONFLICT` | 409 | 다른 사용자가 이미 쓴 request_key | 05 |
| `CSRF_FAILED` | 403 | CSRF 쿠키·헤더 불일치 (D-02) | 공통 |
| `OPERATION_POLICY_UNAVAILABLE` | 503 | 운영 정책 값 이상 또는 (조회 시) 정책 행 없음 (D-27) | 04·05 |
| `NOT_IMPLEMENTED` | 501 | Sprint 2 스켈레톤 (구현 전) | 공통 |
| `INVALID_QR` | 400 | QR 토큰 불일치·형식 오류 | 08 |
| `ALREADY_CHECKED_IN` | 409 | 이미 체크인된 예약 | 08 |
| `RESERVATION_NOT_ACTIVE` | 409 | RESERVED가 아닌 예약(취소·자동 취소·이용 완료)으로 체크인 | 08 |
| `CHECKIN_WINDOW` | 409 | 시작 전 또는 시작+15분 이후 체크인 (D-32) | 08 |
| `NOT_CHECKOUTABLE` | 409 | CHECKED_IN이 아닌 예약 퇴실 | 19 |
| `REASON_REQUIRED` | 400 | 관리자 강제 취소 사유 없음 | 11 |
| `USER_NOT_FOUND` | 404 | 관리자 기능 대상 학생 없음 | 13·14·17 |
| `INVALID_RESTRICTION_DATE` | 400 | 오늘 이전 날짜로 수동 제한 | 14 |
| `INVALID_POLICY` | 400 | 정책 값 조합 이상 (저장 전 검사, D-45) | 15 |
| `INVALID_PERIOD` | 400 | 통계 시작일 > 종료일 | 16 |
| `CANNOT_CHANGE_OWN_ROLE` | 400 | 본인 관리자 권한 회수 | 17 |

- 운영 정책의 시간 설정이 잘못되면 좌석 조회·예약 모두 `503 OPERATION_POLICY_UNAVAILABLE`을 반환합니다. (좌석 조회는 정책 행이 없을 때도 503)
- 시간 검증 규칙은 `app/services/booking_rules.py` 한 곳에서 관리합니다. 조회는 진행 중 시간대까지 허용하고, 예약은 시작 시각이 지나면 거부합니다.

## 인증 구현 메모 (2026-11-18)

- 가입 메일에 `/verify-email?token=...` 링크와 6자리 코드를 함께 제공한다. 둘 중 하나로 인증하면 나머지도 무효화한다. 기본 유효시간은 10분이다.
- 링크의 호스트는 `PUBLIC_BASE_URL`, 학교 도메인은 `ALLOWED_EMAIL_DOMAIN`으로 지정한다. 도메인을 비우면 기존 설정 계약대로 도메인 제한을 생략한다.
- 로그인 응답 본문은 기존 `LoginResponse`를 유지한다. Refresh 원문은 HttpOnly 쿠키로만 발급하고 DB에는 해시만 저장한다.
- Access·Refresh 쿠키는 HttpOnly·SameSite=Lax·Path=/, CSRF는 JS 읽기 가능이다. 배포 HTTPS에서는 `COOKIE_SECURE=true`로 설정한다.
- Refresh는 Access 만료 후에도 호출할 수 있다. CSRF 쿠키는 Refresh 수명 동안 유지하며, Refresh 자체의 만료 시각은 갱신하지 않는다. 진행 중 요청이 거부되지 않도록 Refresh 때 기존 CSRF 값을 유지한다.
- 브라우저는 보호된 API의 401 발생 시 Refresh 후 한 번 재시도한다. 로그인 실패에는 자동 Refresh를 수행하지 않는다.
- 로그아웃은 현재 세션만 폐기한다. 다른 기기·브라우저의 세션은 유지한다.
- BCrypt 입력 한계에 맞춰 비밀번호는 UTF-8 72바이트까지 허용하며, 초과 시 조용히 잘라 저장하지 않고 규칙을 안내한다.
