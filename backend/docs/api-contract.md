# API 계약 — Sprint 1

설계서 4장(REST Endpoint Catalog) 중 Sprint 1 범위. 필드명은 `app/schemas/*.py`가 기준이며, 바꾸면 이 문서도 같은 PR에서 수정합니다.

## 공통

- 날짜·시간: ISO-8601, 한국 시간(KST) 기준 timezone 없는 값 — `2026-11-20T10:00:00`
- 인증: HttpOnly 쿠키 `access_token` (화면) 또는 `Authorization: Bearer <token>` (Swagger/테스트)
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
| POST | `/api/auth/email-verifications` | 공개 | 01 | `EmailVerifyRequest` | `MessageResponse` |
| POST | `/api/auth/login` | 공개 | 02·03 | `LoginRequest` | `LoginResponse` + 쿠키 |
| POST | `/api/auth/logout` | 로그인 | 02 | - | `MessageResponse` |
| GET | `/api/auth/me` | 로그인 | 02 | - | `MeResponse` |
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
| `ACCOUNT_LOCKED` | 403 | 로그인 실패 잠금 | 03 |
| `PASSWORD_POLICY` | 400 | 8자 미만 / 영문·숫자·특수문자 누락 | 01 |
| `DUPLICATE_STUDENT_NO` | 409 | 학번 중복 | 01 |
| `DUPLICATE_EMAIL` | 409 | 이메일 중복 | 01 |
| `INVALID_VERIFICATION` | 400 | 인증 코드 불일치·만료 | 01 |
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
| `NOT_CANCELLABLE` | 409 | RESERVED가 아닌 예약 취소 | 09 |
