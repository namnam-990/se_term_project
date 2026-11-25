// US-08 체크인 단말 (Sprint 2 스켈레톤) — 담당: US-08 담당자
// D-30: 관리자 로그인 상태의 단말기가 학생 QR을 스캔 → POST /api/reservations/{id}/check-in {token}
// D-31: 카메라 스캔만. jsQR(app/static/vendor/jsQR.js) 추가 후 구현.
// QR 문자열 형식 (D-29, app/services/qr_service.py): "LSRS|r=<예약ID>|seat=<좌석>|t=<토큰>"
const kioskMessage = document.getElementById("kiosk-message");

function parseQrPayload(text) {
  const parts = String(text).trim().split("|");
  if (parts.length !== 4 || parts[0] !== "LSRS") return null;
  const fields = Object.fromEntries(parts.slice(1).map((p) => p.split("=", 2)));
  if (!/^\d+$/.test(fields.r || "") || !fields.t) return null;
  return { reservationId: Number(fields.r), seat: fields.seat, token: fields.t };
}

// TODO(US-08): 웹캠 시작 → 프레임마다 jsQR → parseQrPayload → api(`/api/reservations/${id}/check-in`, {method:"POST", body:{token}})
kioskMessage.textContent = "체크인 단말 화면은 아직 구현 중입니다 (US-08).";
