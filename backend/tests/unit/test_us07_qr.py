"""US-07 예약 확정 좌석의 체크인용 QR 발급 — FR-C-01 (Must / 2 SP) · D-29·D-33"""

import pytest

from app.models import ReservationStatus
from app.services.qr_service import build_payload, parse_payload, qr_token

pending = pytest.mark.skip(reason="US-07 구현 전 — 구현 후 이 데코레이터를 지우세요")


def _qr(client, headers, rid):
    return client.get(f"/api/reservations/{rid}/qr", headers=headers)


# ── QR 문자열 약속 (US-07·08 공용, 미리 구현됨) ──
def test_payload_roundtrip_and_token_is_fixed_per_reservation():
    payload = build_payload(12, "A-01")
    assert payload.startswith("LSRS|r=12|seat=A-01|t=")
    assert parse_payload(payload) == (12, qr_token(12))
    assert qr_token(12) == qr_token(12)  # 다시 열어도 같은 QR (D-33)
    assert qr_token(12) != qr_token(13)


@pytest.mark.parametrize("text", ["", "hello", "LSRS|r=x|seat=A-01|t=abc", "XX|r=1|seat=A|t=abc"])
def test_parse_payload_rejects_invalid(text):
    assert parse_payload(text) is None


# ── AC ──
@pending
def test_us07_ac1_reserved_shows_qr_with_seat_info(
    client, policy, seats, make_user, auth_headers, make_reservation
):
    """Given RESERVED When 예약 QR 조회 Then 좌석 정보가 담긴 QR 표시 (FR-C-01)"""
    me = make_user()
    r = make_reservation(me, seats[0], "10:00", "12:00")
    body = _qr(client, auth_headers(me), r.id).json()
    assert body["active"] is True
    assert body["payload"] == build_payload(r.id, "A-01")
    assert body["svg"].lstrip().startswith("<svg")
    assert _qr(client, auth_headers(me), r.id).json()["payload"] == body["payload"]  # D-33


@pending
@pytest.mark.parametrize("status", [ReservationStatus.CANCELLED, ReservationStatus.AUTO_CANCELLED])
def test_us07_ac2_cancelled_reservation_qr_inactive(
    client, policy, seats, make_user, auth_headers, make_reservation, status
):
    """Given 취소·자동 취소 When QR 조회 Then 비활성 + 사용 불가 안내 (D-33)"""
    me = make_user()
    r = make_reservation(me, seats[0], "10:00", "12:00", status=status)
    body = _qr(client, auth_headers(me), r.id).json()
    assert body["active"] is False and body["payload"] is None and body["message"]


@pending
def test_us07_ac3_other_students_qr_forbidden(
    client, policy, seats, make_user, auth_headers, make_reservation
):
    """Given 타인 예약 When QR 조회 Then 403, 코드 노출 없음"""
    owner, other = make_user("202200001"), make_user("202200002")
    r = make_reservation(owner, seats[0], "10:00", "12:00")
    res = _qr(client, auth_headers(other), r.id)
    assert res.status_code == 403 and res.json()["code"] == "NOT_OWNER"
    assert "payload" not in res.json()


@pending
def test_us07_unknown_reservation_404(client, policy, make_user, auth_headers):
    assert _qr(client, auth_headers(make_user()), 9999).status_code == 404
