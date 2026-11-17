# API 계약 — Sprint 1

설계서 4장(REST Endpoint Catalog) 중 Sprint 1 범위. 명세서와 충돌하면 [`decisions.md`](decisions.md)를 따릅니다. 필드명은 `app/schemas/*.py`가 기준이며, 바꾸면 이 문서도 같은 PR에서 수정합니다.

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
| GET | `/api/seats?start_at=&end_at=` | 학생 | 04 | query | `SeatGridResponse` |
| POST | `/api/reservations` | 학생 | 05 | `ReservationCreateRequest` | `ReservationResponse` |
| GET | `/api/me/reservations?status=` | 학생 | 06 | query | `ReservationListResponse` |
| POST | `/api/reservations/{id}/cancel` | 학생(본인) | 09 | `ReservationCancelRequest` | `ReservationResponse` |

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
| `PASSWORD_POLICY` | 400 | 8자 미만 / 영문·숫자·특수문자 누락 | 01 |
| `DUPLICATE_STUDENT_NO` | 409 | 학번 중복 | 01 |
| `DUPLICATE_EMAIL` | 409 | 이메일 중복 | 01 |
| `INVALID_VERIFICATION` | 400 | 인증 코드·링크 불일치·만료 (10분, D-15) | 01 |
| `EMAIL_DOMAIN` | 400 | 학교 이메일 도메인 아님 (`ALLOWED_EMAIL_DOMAIN` 설정 시) | 01 |
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

- 좌석 조회에서 운영 정책이 없거나 시간 설정이 잘못되면 `503 OPERATION_POLICY_UNAVAILABLE`을 반환합니다.
